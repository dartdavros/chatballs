"""WebSocket signaling (проход B, SPEC-HUB-0013 §9): auth по access token,
relay только между участниками звонка, переходы CONNECTING/ACTIVE/ENDED,
reconnect без новой CallSession, поздние события игнорируются."""

import asyncio
from datetime import timedelta
from unittest import mock

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from django.utils import timezone

from chatballs.calls import consumers
from chatballs.calls.models import (
    CallParticipant,
    CallSession,
    CallStatus,
    ParticipantConnectionState,
    ParticipantSide,
)
from chatballs.calls.services import (
    accept_call_by_access_token,
    open_call_for_identity,
)
from chatballs.calls.tests.helpers import CallDomainMixin, create_call_request, expire_stale_calls
from chatballs.conversations.models import Message
from chatballs_backend.asgi import application

WS_PATH = "/ws/calls/"


class SignalingTestCase(CallDomainMixin, TransactionTestCase):
    # TransactionTestCase: consumer выполняет ORM в отдельных потоках, поэтому
    # транзакционная изоляция обычного TestCase не подходит.
    def _make_accepted_call(self):
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        customer_token = open_call_for_identity(identity=self.identity).customer_access_token
        accept_call_by_access_token(token=customer_token)
        return created, customer_token

    async def _connect(self, token: str) -> WebsocketCommunicator:
        communicator = WebsocketCommunicator(application, WS_PATH)
        connected, _ = await communicator.connect()
        assert connected
        await communicator.send_json_to({"type": "auth", "token": token})
        state = await communicator.receive_json_from()
        assert state["type"] == "call.state", state
        return communicator

    async def _drain_until(self, communicator: WebsocketCommunicator, msg_type: str, limit: int = 10) -> dict:
        for _ in range(limit):
            message = await communicator.receive_json_from()
            if message["type"] == msg_type:
                return message
        raise AssertionError(f"no {msg_type} received")


class SignalingAuthTests(SignalingTestCase):
    def test_invalid_token_is_rejected(self) -> None:
        async def scenario():
            communicator = WebsocketCommunicator(application, WS_PATH)
            connected, _ = await communicator.connect()
            assert connected
            await communicator.send_json_to({"type": "auth", "token": "garbage"})
            message = await communicator.receive_json_from()
            self.assertEqual(message, {"type": "error", "code": "AUTH_FAILED"})
            await communicator.wait()

        async_to_sync(scenario)()

    def test_first_message_must_be_auth(self) -> None:
        async def scenario():
            communicator = WebsocketCommunicator(application, WS_PATH)
            await communicator.connect()
            await communicator.send_json_to({"type": "webrtc.offer", "sdp": "x"})
            output = await communicator.receive_output()
            self.assertEqual(output["type"], "websocket.close")

        async_to_sync(scenario)()

    def test_join_marks_presence_without_new_session(self) -> None:
        created, customer_token = self._make_accepted_call()

        async def scenario():
            communicator = await self._connect(customer_token)
            await communicator.disconnect()
            # Повторное подключение — reconnect, не новый звонок.
            second = await self._connect(customer_token)
            await second.disconnect()

        async_to_sync(scenario)()
        self.assertEqual(CallSession.objects.count(), 1)
        participant = CallParticipant.objects.get(call_session=created.call_session, side=ParticipantSide.CUSTOMER)
        self.assertIsNotNone(participant.joined_at)
        self.assertEqual(participant.last_connection_state, ParticipantConnectionState.DISCONNECTED)


class SignalingRelayTests(SignalingTestCase):
    def test_offer_relays_to_peer_and_moves_call_to_connecting(self) -> None:
        created, customer_token = self._make_accepted_call()
        staff_token = created.staff_access_token

        async def scenario():
            staff = await self._connect(staff_token)
            customer = await self._connect(customer_token)
            await self._drain_until(staff, "peer.joined")
            await staff.send_json_to({"type": "webrtc.offer", "id": "offer-1", "sdp": "fake-sdp"})
            relayed = await self._drain_until(customer, "webrtc.offer")
            self.assertEqual(relayed["sdp"], "fake-sdp")
            self.assertEqual(relayed["side"], ParticipantSide.STAFF)
            # Повтор с тем же idempotency id не ретранслируется.
            await staff.send_json_to({"type": "webrtc.offer", "id": "offer-1", "sdp": "fake-sdp"})
            await staff.send_json_to({"type": "webrtc.ice_candidate", "id": "ice-1", "candidate": "c1"})
            second = await self._drain_until(customer, "webrtc.ice_candidate")
            self.assertEqual(second["candidate"], "c1")
            await staff.disconnect()
            await customer.disconnect()

        async_to_sync(scenario)()
        created.call_session.refresh_from_db()
        self.assertEqual(created.call_session.status, CallStatus.CONNECTING)
        # SDP не сохраняется нигде в БД.
        self.assertFalse(Message.objects.filter(text__icontains="fake-sdp").exists())

    def test_active_requires_both_sides_connected(self) -> None:
        created, customer_token = self._make_accepted_call()

        async def scenario():
            staff = await self._connect(created.staff_access_token)
            customer = await self._connect(customer_token)
            await staff.send_json_to({"type": "participant.connection_state", "id": "s1", "state": "CONNECTED"})
            await customer.send_json_to({"type": "participant.connection_state", "id": "c1", "state": "CONNECTED"})
            state = await self._drain_until(customer, "call.state")
            self.assertEqual(state["call"]["status"], CallStatus.ACTIVE)
            await staff.disconnect()
            await customer.disconnect()

        async_to_sync(scenario)()
        created.call_session.refresh_from_db()
        self.assertEqual(created.call_session.status, CallStatus.ACTIVE)
        self.assertIsNotNone(created.call_session.connected_at)
        self.assertTrue(
            Message.objects.filter(conversation=self.conversation, text__icontains="соединение установлено").exists()
        )

    def test_end_from_active_is_idempotent_with_duration(self) -> None:
        created, customer_token = self._make_accepted_call()

        async def scenario():
            staff = await self._connect(created.staff_access_token)
            customer = await self._connect(customer_token)
            await staff.send_json_to({"type": "participant.connection_state", "id": "s1", "state": "CONNECTED"})
            await customer.send_json_to({"type": "participant.connection_state", "id": "c1", "state": "CONNECTED"})
            await self._drain_until(staff, "call.state")
            await staff.send_json_to({"type": "call.ended", "id": "end-1"})
            ended = await self._drain_until(customer, "call.state", limit=15)
            while ended["call"]["status"] != CallStatus.ENDED:
                ended = await self._drain_until(customer, "call.state", limit=15)
            await customer.send_json_to({"type": "call.ended", "id": "end-2"})
            await staff.disconnect()
            await customer.disconnect()

        async_to_sync(scenario)()
        call = CallSession.objects.get()
        self.assertEqual(call.status, CallStatus.ENDED)
        self.assertEqual(call.ended_by, "STAFF")
        self.assertIsNotNone(call.duration_seconds)
        self.assertEqual(Message.objects.filter(text__icontains="Звонок завершён").count(), 1)

    def test_late_events_after_end_are_ignored(self) -> None:
        created, customer_token = self._make_accepted_call()

        async def scenario():
            staff = await self._connect(created.staff_access_token)
            customer = await self._connect(customer_token)
            await staff.send_json_to({"type": "call.ended", "id": "end-1"})
            await self._drain_until(customer, "call.state")
            await staff.send_json_to({"type": "webrtc.offer", "id": "late-1", "sdp": "late"})
            self.assertTrue(await customer.receive_nothing(timeout=0.3))
            await staff.disconnect()
            await customer.disconnect()

        async_to_sync(scenario)()

    def test_end_before_connect_becomes_failed(self) -> None:
        created, customer_token = self._make_accepted_call()

        async def scenario():
            customer = await self._connect(customer_token)
            await customer.send_json_to({"type": "call.ended", "id": "end-1"})
            state = await self._drain_until(customer, "call.state")
            self.assertEqual(state["call"]["status"], CallStatus.FAILED)
            await customer.disconnect()

        async_to_sync(scenario)()
        call = CallSession.objects.get()
        self.assertEqual(call.failure_code, "ABORTED_BEFORE_CONNECT")
        self.assertEqual(call.ended_by, "CUSTOMER")


class ReconnectSweepTests(SignalingTestCase):
    def test_active_call_fails_after_reconnect_grace(self) -> None:
        created, customer_token = self._make_accepted_call()

        async def scenario():
            staff = await self._connect(created.staff_access_token)
            customer = await self._connect(customer_token)
            await staff.send_json_to({"type": "participant.connection_state", "id": "s1", "state": "CONNECTED"})
            await customer.send_json_to({"type": "participant.connection_state", "id": "c1", "state": "CONNECTED"})
            await self._drain_until(staff, "call.state")
            await customer.disconnect()  # клиент пропал и не вернулся
            await staff.disconnect()

        async_to_sync(scenario)()
        CallParticipant.objects.filter(
            call_session=created.call_session, side=ParticipantSide.CUSTOMER
        ).update(left_at=timezone.now() - timedelta(hours=1))
        expire_stale_calls(self.organization)
        call = CallSession.objects.get()
        self.assertEqual(call.status, CallStatus.FAILED)
        self.assertEqual(call.failure_code, "PEER_DISCONNECTED")

    def test_reconnect_within_grace_keeps_call_active(self) -> None:
        created, customer_token = self._make_accepted_call()

        async def scenario():
            staff = await self._connect(created.staff_access_token)
            customer = await self._connect(customer_token)
            await staff.send_json_to({"type": "participant.connection_state", "id": "s1", "state": "CONNECTED"})
            await customer.send_json_to({"type": "participant.connection_state", "id": "c1", "state": "CONNECTED"})
            await self._drain_until(staff, "call.state")
            await customer.disconnect()
            # Вернулся: presence восстановлен, left_at сброшен.
            customer_again = await self._connect(customer_token)
            await customer_again.send_json_to(
                {"type": "participant.connection_state", "id": "c2", "state": "CONNECTED"}
            )
            relayed = await self._drain_until(staff, "participant.connection_state")
            while relayed["state"] != "CONNECTED":
                relayed = await self._drain_until(staff, "participant.connection_state")
            await customer_again.disconnect()
            await staff.disconnect()

        async_to_sync(scenario)()
        # Обрыва не осталось (left_at сброшен reconnect'ом до дисконнекта в
        # конце сценария) — недавний left_at не старше grace, звонок жив.
        expire_stale_calls(self.organization)
        call = CallSession.objects.get()
        self.assertEqual(call.status, CallStatus.ACTIVE)


class AuthDeadlineTests(CallDomainMixin, TransactionTestCase):
    """Соединение принимается до аутентификации — значит, ждать оно должно не вечно."""

    def test_unauthenticated_socket_is_closed_on_deadline(self) -> None:
        async def scenario():
            communicator = WebsocketCommunicator(application, WS_PATH)
            connected, _ = await communicator.connect()
            assert connected
            # Токен не присылаем вовсе: сокет обязан закрыться сам.
            output = await communicator.receive_output(timeout=5)
            await communicator.disconnect()
            return output

        with mock.patch.object(consumers, "AUTH_TIMEOUT_SECONDS", 0.1):
            output = async_to_sync(scenario)()

        self.assertEqual(output["type"], "websocket.close")
        self.assertEqual(output["code"], consumers.AUTH_TIMEOUT_CLOSE)

    def test_authenticated_socket_survives_the_deadline(self) -> None:
        created, customer_token = None, None

        def prepare():
            create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
            return open_call_for_identity(identity=self.identity).customer_access_token

        customer_token = prepare()

        async def scenario(token: str):
            communicator = WebsocketCommunicator(application, WS_PATH)
            connected, _ = await communicator.connect()
            assert connected
            await communicator.send_json_to({"type": "auth", "token": token})
            state = await communicator.receive_json_from()
            # Пережидаем срок: у аутентифицированного соединения он снят.
            await asyncio.sleep(0.3)
            nothing_left = await communicator.receive_nothing(timeout=0.2)
            await communicator.disconnect()
            return state, nothing_left

        with mock.patch.object(consumers, "AUTH_TIMEOUT_SECONDS", 0.1):
            state, nothing_left = async_to_sync(scenario)(customer_token)

        self.assertEqual(state["type"], "call.state")
        self.assertTrue(nothing_left)
