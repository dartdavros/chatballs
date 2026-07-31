import json

from hub_platform.testing import TenantAPIClient as APIClient

from hub_platform.calls.models import CallKind, CallSession, CallStatus, ParticipantSide
from hub_platform.calls.tests.helpers import CallTestCase, create_call_request
from hub_platform.calls.tokens import verify_call_access_token
from hub_platform.conversations.models import ControlMode


class InternalCallApiTests(CallTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_create_call_returns_staff_token_but_not_invite_token(self) -> None:
        response = self.client.post(
            f"/api/v1/calls/conversations/{self.conversation.id}/",
            data=json.dumps({"kind": "AUDIO"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        # WEB-подключение: доставка поллингом виджета, звонок сразу RINGING.
        self.assertEqual(payload["call"]["status"], CallStatus.RINGING)
        self.assertEqual(payload["call"]["kind"], CallKind.AUDIO)
        self.assertNotIn("inviteToken", payload)
        self.assertNotIn("tokenHash", json.dumps(payload))
        self.assertEqual(response["Cache-Control"], "no-store")
        claims = verify_call_access_token(payload["staffAccessToken"])
        self.assertEqual(claims.side, ParticipantSide.STAFF)
        self.assertEqual(CallSession.objects.count(), 1)

    def test_create_call_conflict_returns_409(self) -> None:
        first = self.client.post(
            f"/api/v1/calls/conversations/{self.conversation.id}/",
            data=json.dumps({"kind": "VIDEO"}),
            content_type="application/json",
        )
        second = self.client.post(
            f"/api/v1/calls/conversations/{self.conversation.id}/",
            data=json.dumps({"kind": "VIDEO"}),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(set(second.json()), {"detail"})

    def test_other_department_operator_gets_403_without_takeover(self) -> None:
        support_operator = self.create_support_operator()
        self.client.force_authenticate(user=support_operator)
        response = self.client.post(
            f"/api/v1/calls/conversations/{self.conversation.id}/",
            data=json.dumps({"kind": "VIDEO"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CallSession.objects.exists())
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.control_mode, ControlMode.AI)

    def test_create_call_requires_explicit_kind(self) -> None:
        response = self.client.post(f"/api/v1/calls/conversations/{self.conversation.id}/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Укажите тип звонка"})
        self.assertFalse(CallSession.objects.exists())

    def test_staff_participant_can_refresh_access_token(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        response = self.client.post(f"/api/v1/calls/{created.call_session.id}/access-token/")
        self.assertEqual(response.status_code, 200)
        claims = verify_call_access_token(response.json()["accessToken"])
        self.assertEqual(claims.call_session_id, created.call_session.id)
        self.assertIn("iceServers", response.json())


class PublicInviteApiTests(CallTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()

    def test_resolve_returns_minimal_call_context_and_customer_token(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        response = self.client.post(
            "/api/v1/calls/invites/resolve/",
            data=json.dumps({"token": created.invite_token}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(
            set(payload["call"]),
            {"callId", "status", "kind", "expiresAt", "staffName"},
        )
        self.assertNotIn("conversation", json.dumps(payload))
        self.assertNotIn(created.invite_token, json.dumps(payload))
        claims = verify_call_access_token(payload["accessToken"])
        self.assertEqual(claims.side, ParticipantSide.CUSTOMER)

    def test_invalid_invites_have_same_terminal_response(self) -> None:
        response = self.client.post(
            "/api/v1/calls/invites/resolve/",
            data=json.dumps({"token": "invalid"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Недействительное или истёкшее приглашение"})
