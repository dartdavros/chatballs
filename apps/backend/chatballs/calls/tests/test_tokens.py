from datetime import timedelta
import uuid

from django.test import override_settings
from django.utils import timezone

from chatballs.calls.errors import CallTokenError
from chatballs.calls.lifecycle import transition_call
from chatballs.calls.models import CallStatus, ParticipantSide
from chatballs.calls.services import (
    authorize_call_access_token,
    resolve_invite,
)
from chatballs.calls.tests.helpers import CallTestCase, create_call_request
from chatballs.calls.tokens import (
    issue_call_access_token,
    verify_call_access_token,
)


class InviteTokenTests(CallTestCase):
    def test_invite_resolves_without_storing_raw_token(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        self.assertNotIn(created.invite_token, created.call_session.invite.token_hash)

        resolved = resolve_invite(token=created.invite_token)

        self.assertEqual(resolved.invite.call_session_id, created.call_session.id)
        self.assertIsNotNone(resolved.invite.opened_at)
        claims, call = authorize_call_access_token(token=resolved.customer_access_token)
        self.assertEqual(call.id, created.call_session.id)
        self.assertEqual(claims.side, ParticipantSide.CUSTOMER)
        self.assertEqual(claims.subject_id, str(resolved.invite.id))

    def test_invalid_invite_is_indistinguishable(self) -> None:
        with self.assertRaisesMessage(CallTokenError, "Недействительное или истёкшее приглашение"):
            resolve_invite(token="invalid-token")

    def test_invite_token_can_be_exchanged_only_once(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        resolve_invite(token=created.invite_token)
        with self.assertRaisesMessage(CallTokenError, "Недействительное или истёкшее приглашение"):
            resolve_invite(token=created.invite_token)

    def test_expired_invite_is_rejected(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        created.call_session.invite.expires_at = timezone.now() - timedelta(seconds=1)
        created.call_session.invite.save(update_fields=["expires_at"])
        with self.assertRaises(CallTokenError):
            resolve_invite(token=created.invite_token)

    def test_terminal_call_invalidates_invite(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        transition_call(
            call_session_id=created.call_session.id,
            target_status=CallStatus.CANCELLED,
        )
        with self.assertRaises(CallTokenError):
            resolve_invite(token=created.invite_token)


class AccessTokenTests(CallTestCase):
    def test_staff_access_token_is_bound_to_participant(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        claims, call = authorize_call_access_token(token=created.staff_access_token)
        self.assertEqual(call.id, created.call_session.id)
        self.assertEqual(claims.side, ParticipantSide.STAFF)
        self.assertEqual(claims.subject_id, str(self.owner.id))

    def test_tampered_access_token_is_rejected(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        token = created.staff_access_token
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with self.assertRaises(CallTokenError):
            verify_call_access_token(tampered)

    def test_malformed_access_token_is_rejected_without_decode_error(self) -> None:
        with self.assertRaises(CallTokenError):
            verify_call_access_token("%%%.$$$")

    @override_settings(CHATBALLS_CALL_ACCESS_TTL_SECONDS=-1)
    def test_expired_access_token_is_rejected(self) -> None:
        token = issue_call_access_token(
            call_session_id=uuid.uuid4(),
            side=ParticipantSide.STAFF,
            subject_id=str(self.owner.id),
        )
        with self.assertRaises(CallTokenError):
            verify_call_access_token(token)

    def test_terminal_call_invalidates_access_token(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        transition_call(
            call_session_id=created.call_session.id,
            target_status=CallStatus.CANCELLED,
        )
        with self.assertRaises(CallTokenError):
            authorize_call_access_token(token=created.staff_access_token)
