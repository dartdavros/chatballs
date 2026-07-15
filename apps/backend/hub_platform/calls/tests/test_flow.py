"""Контур приглашений (проход A, E09): отмена/принятие/отклонение, доставка
TG/MAX через outbox, истечение и системные события в timeline."""

import json
from datetime import timedelta
from unittest import mock

from django.utils import timezone
from hub_platform.testing import TenantAPIClient as APIClient, tenant_context_for

from hub_platform.calls.event_handlers import handle_call_invite_send
from hub_platform.calls.models import (
    CallEndedBy,
    CallInvite,
    CallSession,
    CallStatus,
    InviteDeliveryStatus,
)
from hub_platform.calls.services import (
    open_call_for_identity,
    decline_call_for_identity,
)
from hub_platform.calls.tests.helpers import CallTestCase, create_call_request, expire_stale_calls
from hub_platform.calls.tokens import hash_invite_token
from hub_platform.conversations.models import Conversation, Message
from hub_platform.events.models import OutboxEvent
from hub_platform.integrations.models import Integration, IntegrationKind, IntegrationProvider


class CancelCallApiTests(CallTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_initiator_cancels_pending_call(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        response = self.client.post(f"/api/v1/calls/{created.call_session.id}/cancel/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["call"]["status"], CallStatus.CANCELLED)
        created.call_session.refresh_from_db()
        self.assertEqual(created.call_session.ended_by, CallEndedBy.STAFF)
        self.assertTrue(
            Message.objects.filter(
                conversation=self.conversation, text="Сотрудник отменил приглашение на звонок"
            ).exists()
        )

    def test_cancel_is_idempotent(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        first = self.client.post(f"/api/v1/calls/{created.call_session.id}/cancel/")
        second = self.client.post(f"/api/v1/calls/{created.call_session.id}/cancel/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            Message.objects.filter(
                conversation=self.conversation, text="Сотрудник отменил приглашение на звонок"
            ).count(),
            1,
        )

    def test_non_participant_cannot_cancel(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        self.client.force_authenticate(user=self.operator)
        response = self.client.post(f"/api/v1/calls/{created.call_session.id}/cancel/")
        self.assertEqual(response.status_code, 409)
        created.call_session.refresh_from_db()
        self.assertEqual(created.call_session.status, CallStatus.RINGING)

    def test_active_call_lookup_for_conversation(self) -> None:
        empty = self.client.get(f"/api/v1/calls/conversations/{self.conversation.id}/active/")
        self.assertEqual(empty.status_code, 200)
        self.assertIsNone(empty.json()["call"])
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        response = self.client.get(f"/api/v1/calls/conversations/{self.conversation.id}/active/")
        self.assertEqual(response.json()["call"]["id"], str(created.call_session.id))


class CustomerAccessApiTests(CallTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()

    def _customer_token(self) -> str:
        create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        return open_call_for_identity(identity=self.identity).customer_access_token

    def _post(self, path: str, token: str):
        return self.client.post(path, HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_customer_accepts_call(self) -> None:
        token = self._customer_token()
        response = self._post("/api/v1/calls/access/accept/", token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["call"]["status"], CallStatus.ACCEPTED)
        self.assertTrue(
            Message.objects.filter(
                conversation=self.conversation, text="Клиент принял приглашение на звонок"
            ).exists()
        )

    def test_accept_is_idempotent_without_duplicate_events(self) -> None:
        token = self._customer_token()
        self._post("/api/v1/calls/access/accept/", token)
        second = self._post("/api/v1/calls/access/accept/", token)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            Message.objects.filter(
                conversation=self.conversation, text="Клиент принял приглашение на звонок"
            ).count(),
            1,
        )

    def test_customer_declines_call(self) -> None:
        token = self._customer_token()
        response = self._post("/api/v1/calls/access/decline/", token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["call"]["status"], CallStatus.DECLINED)
        call = CallSession.objects.get()
        self.assertEqual(call.ended_by, CallEndedBy.CUSTOMER)
        self.assertIsNotNone(call.invite.responded_at)

    def test_state_visible_after_cancellation(self) -> None:
        token = self._customer_token()
        call = CallSession.objects.get()
        from hub_platform.calls.services import cancel_call

        cancel_call(
            context=tenant_context_for(self.owner, self.organization),
            call_session=call,
        )
        response = self._post("/api/v1/calls/access/state/", token)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("iceServers", body)
        payload = body["call"]
        self.assertEqual(payload["status"], CallStatus.CANCELLED)
        self.assertEqual(set(payload), {"callId", "status", "staffName", "endedBy", "durationSeconds"})

    def test_accept_after_cancel_is_rejected(self) -> None:
        token = self._customer_token()
        from hub_platform.calls.services import cancel_call

        cancel_call(
            context=tenant_context_for(self.owner, self.organization),
            call_session=CallSession.objects.get(),
        )
        response = self._post("/api/v1/calls/access/accept/", token)
        self.assertEqual(response.status_code, 404)

    def test_state_requires_valid_token(self) -> None:
        response = self._post("/api/v1/calls/access/state/", "garbage")
        self.assertEqual(response.status_code, 404)


class WebchatCallFlowTests(CallTestCase):
    def test_open_issues_customer_token_and_marks_opened(self) -> None:
        create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        resolved = open_call_for_identity(identity=self.identity)
        self.assertIsNotNone(resolved.invite.opened_at)
        # Повторное открытие (перезагрузка виджета) не отзывает приглашение.
        again = open_call_for_identity(identity=self.identity)
        self.assertEqual(again.invite.id, resolved.invite.id)

    def test_decline_from_widget(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        declined = decline_call_for_identity(identity=self.identity)
        self.assertEqual(declined.id, created.call_session.id)
        self.assertEqual(declined.status, CallStatus.DECLINED)

    def test_poll_payload_contains_invite(self) -> None:
        from hub_platform.webchat.models import WebSession
        from hub_platform.webchat.services import messages_payload

        session = WebSession.objects.create(
            token_hash="x" * 64, connection=self.connection, identity=self.identity
        )
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        payload = messages_payload(session, 0)
        self.assertEqual(payload["call"]["callId"], str(created.call_session.id))
        self.assertEqual(payload["call"]["status"], CallStatus.RINGING)
        decline_call_for_identity(identity=self.identity)
        self.assertIsNone(messages_payload(session, 0)["call"])


class MessengerDeliveryTests(CallTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.telegram = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="call-telegram",
            channel=self.channel,
        )
        self.identity.connection = self.telegram
        self.identity.save(update_fields=["connection"])
        self.conversation.connection = self.telegram
        self.conversation.external_chat_id = "chat-42"
        self.conversation.save(update_fields=["connection", "external_chat_id"])

    def test_create_enqueues_outbox_without_raw_token(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        self.assertEqual(created.call_session.status, CallStatus.REQUESTED)
        event = OutboxEvent.objects.get(event_type="calls.invite_send")
        self.assertEqual(event.payload, {"callSessionId": str(created.call_session.id)})
        self.assertNotIn(created.invite_token, json.dumps(event.payload))

    def test_delivery_sends_button_and_moves_to_ringing(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        sent_kwargs = {}

        def fake_send(integration, **kwargs):
            sent_kwargs.update(kwargs)
            return True

        with mock.patch(
            "hub_platform.calls.event_handlers.transports.send_call_invite", side_effect=fake_send
        ):
            handle_call_invite_send(
                {"callSessionId": str(created.call_session.id)},
                tenant_context_for(self.owner, self.organization),
            )

        call = CallSession.objects.get()
        invite = call.invite
        self.assertEqual(call.status, CallStatus.RINGING)
        self.assertEqual(invite.delivery_status, InviteDeliveryStatus.SENT)
        self.assertEqual(sent_kwargs["chat_id"], "chat-42")
        # Ссылка содержит свежий token; в БД хранится только его hash.
        url_token = sent_kwargs["url"].rsplit("/", 1)[1]
        self.assertEqual(hash_invite_token(url_token), invite.token_hash)
        self.assertNotEqual(url_token, created.invite_token)

    def test_failed_delivery_keeps_call_requested_for_retry(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        old_hash = created.call_session.invite.token_hash
        with mock.patch(
            "hub_platform.calls.event_handlers.transports.send_call_invite", return_value=False
        ):
            with self.assertRaises(Exception):
                handle_call_invite_send(
                    {"callSessionId": str(created.call_session.id)},
                    tenant_context_for(self.owner, self.organization),
                )
        call = CallSession.objects.get()
        self.assertEqual(call.status, CallStatus.REQUESTED)
        self.assertEqual(call.invite.delivery_status, InviteDeliveryStatus.PENDING)
        self.assertEqual(call.invite.token_hash, old_hash)

    def test_repeated_delivery_is_idempotent(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        with mock.patch(
            "hub_platform.calls.event_handlers.transports.send_call_invite", return_value=True
        ) as sender:
            context = tenant_context_for(self.owner, self.organization)
            handle_call_invite_send({"callSessionId": str(created.call_session.id)}, context)
            handle_call_invite_send({"callSessionId": str(created.call_session.id)}, context)
        self.assertEqual(sender.call_count, 1)


class ExpirySweepTests(CallTestCase):
    def _expire_invite(self, call: CallSession) -> None:
        CallInvite.objects.filter(call_session=call).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

    def test_ringing_call_becomes_missed(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        self._expire_invite(created.call_session)
        expire_stale_calls(self.organization)
        call = CallSession.objects.get()
        self.assertEqual(call.status, CallStatus.MISSED)
        self.assertEqual(call.ended_by, CallEndedBy.TIMEOUT)
        self.assertTrue(
            Message.objects.filter(
                conversation=self.conversation, text="Звонок пропущен: клиент не ответил"
            ).exists()
        )

    def test_undelivered_call_becomes_expired(self) -> None:
        # TG-доставка не состоялась: звонок остался REQUESTED.
        self.conversation.connection = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="call-telegram-2",
            channel=self.channel,
        )
        self.conversation.save(update_fields=["connection"])
        self.identity.connection = self.conversation.connection
        self.identity.save(update_fields=["connection"])
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        self._expire_invite(created.call_session)
        expire_stale_calls(self.organization)
        self.assertEqual(CallSession.objects.get().status, CallStatus.EXPIRED)

    def test_accepted_call_without_connection_fails_after_grace(self) -> None:
        create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        token = open_call_for_identity(identity=self.identity).customer_access_token
        from hub_platform.calls.services import accept_call_by_access_token

        accept_call_by_access_token(token=token)
        CallSession.objects.update(accepted_at=timezone.now() - timedelta(hours=1))
        expire_stale_calls(self.organization)
        call = CallSession.objects.get()
        self.assertEqual(call.status, CallStatus.FAILED)
        self.assertEqual(call.failure_code, "CONNECT_TIMEOUT")

    def test_sweep_is_idempotent(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        self._expire_invite(created.call_session)
        expire_stale_calls(self.organization)
        expire_stale_calls(self.organization)
        self.assertEqual(
            Message.objects.filter(
                conversation=self.conversation, text="Звонок пропущен: клиент не ответил"
            ).count(),
            1,
        )


class TimelineEventTests(CallTestCase):
    def test_request_creates_single_system_event(self) -> None:
        create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        self.assertEqual(
            Message.objects.filter(
                conversation=self.conversation, text__icontains="запросил онлайн-звонок"
            ).count(),
            1,
        )

    def test_conversation_lifecycle_is_untouched_by_call_events(self) -> None:
        create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        decline_call_for_identity(identity=self.identity)
        conversation = Conversation.objects.get(id=self.conversation.id)
        self.assertEqual(conversation.lifecycle, "OPEN")
