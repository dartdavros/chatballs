from django.db import IntegrityError, transaction

from hub_platform.calls.errors import CallAccessDenied, CallConflict, CallInvalidTransition
from hub_platform.calls.lifecycle import transition_call
from hub_platform.calls.models import (
    CallEndedBy,
    CallParticipant,
    CallSession,
    CallStatus,
    ParticipantSide,
)
from hub_platform.calls.tests.helpers import CallTestCase, create_call_request
from hub_platform.calls.tokens import hash_invite_token
from hub_platform.conversations.models import ControlMode, LifecycleState, Message


class CallCreationTests(CallTestCase):
    def test_creation_claims_conversation_and_builds_domain(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)

        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.control_mode, ControlMode.HUMAN)
        self.assertEqual(self.conversation.assigned_operator, self.owner)
        # WEB-подключение: доставка поллингом виджета, звонок сразу RINGING.
        self.assertEqual(created.call_session.status, CallStatus.RINGING)
        self.assertEqual(created.call_session.organization, self.organization)
        self.assertEqual(created.call_session.delivery_connection, self.connection)
        self.assertNotEqual(created.invite_token, created.call_session.invite.token_hash)
        self.assertEqual(
            hash_invite_token(created.invite_token),
            created.call_session.invite.token_hash,
        )
        self.assertEqual(
            set(created.call_session.participants.values_list("side", flat=True)),
            {ParticipantSide.STAFF, ParticipantSide.CUSTOMER},
        )
        self.assertTrue(Message.objects.filter(conversation=self.conversation, text__icontains="перехватил").exists())

    def test_claim_conflict_rolls_back_everything(self) -> None:
        self.conversation.control_mode = ControlMode.HUMAN
        self.conversation.assigned_operator = self.operator
        self.conversation.save(update_fields=["control_mode", "assigned_operator"])
        message_count = Message.objects.count()

        with self.assertRaises(CallConflict):
            create_call_request(conversation_id=self.conversation.id, initiator=self.owner)

        self.assertFalse(CallSession.objects.exists())
        self.assertFalse(CallParticipant.objects.exists())
        self.assertEqual(Message.objects.count(), message_count)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.assigned_operator, self.operator)

    def test_operator_outside_group_is_denied(self) -> None:
        support_operator = self.create_support_operator()

        with self.assertRaises(CallAccessDenied):
            create_call_request(conversation_id=self.conversation.id, initiator=support_operator)

        self.assertFalse(CallSession.objects.exists())
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.control_mode, ControlMode.AI)

    def test_blocked_operator_is_denied(self) -> None:
        self.operator.memberships.get(organization=self.organization).block()
        with self.assertRaises(CallAccessDenied):
            create_call_request(conversation_id=self.conversation.id, initiator=self.operator)
        self.assertFalse(CallSession.objects.exists())

    def test_closed_conversation_is_rejected(self) -> None:
        self.conversation.lifecycle = LifecycleState.CLOSED
        self.conversation.save(update_fields=["lifecycle"])
        with self.assertRaises(CallConflict):
            create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        self.assertFalse(CallSession.objects.exists())

    def test_missing_connection_identity_does_not_trigger_takeover(self) -> None:
        self.identity.delete()
        with self.assertRaises(CallConflict):
            create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.control_mode, ControlMode.AI)

    def test_ambiguous_connection_identity_does_not_trigger_takeover(self) -> None:
        self.identity.external_user_id = "customer-primary"
        self.identity.save(update_fields=["external_user_id"])
        type(self.identity).objects.create(
            contact=self.contact,
            connection=self.connection,
            external_user_id="customer-secondary",
            display_name="Анна 2",
        )
        with self.assertRaises(CallConflict):
            create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        self.assertFalse(CallSession.objects.exists())
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.control_mode, ControlMode.AI)

    def test_initiator_cannot_have_two_unfinished_calls(self) -> None:
        create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        second = self.create_second_conversation()
        with self.assertRaises(CallConflict):
            create_call_request(conversation_id=second.id, initiator=self.owner)
        self.assertEqual(CallSession.objects.count(), 1)

    def test_database_rejects_second_customer_participant(self) -> None:
        created = create_call_request(conversation_id=self.conversation.id, initiator=self.owner)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CallParticipant.objects.create(
                call_session=created.call_session,
                side=ParticipantSide.CUSTOMER,
                connection_identity=self.identity,
            )


class CallLifecycleTests(CallTestCase):
    def test_happy_path_sets_timestamps_and_duration(self) -> None:
        call = create_call_request(
            conversation_id=self.conversation.id,
            initiator=self.owner,
        ).call_session
        for status in (
            CallStatus.RINGING,
            CallStatus.ACCEPTED,
            CallStatus.CONNECTING,
            CallStatus.ACTIVE,
            CallStatus.ENDED,
        ):
            call = transition_call(
                call_session_id=call.id,
                target_status=status,
                ended_by=CallEndedBy.STAFF,
            )
        self.assertIsNotNone(call.accepted_at)
        self.assertIsNotNone(call.connected_at)
        self.assertIsNotNone(call.ended_at)
        self.assertEqual(call.ended_by, CallEndedBy.STAFF)
        self.assertIsNotNone(call.duration_seconds)

    def test_invalid_transition_is_rejected(self) -> None:
        call = create_call_request(
            conversation_id=self.conversation.id,
            initiator=self.owner,
        ).call_session
        with self.assertRaises(CallInvalidTransition):
            transition_call(call_session_id=call.id, target_status=CallStatus.ACTIVE)

    def test_failed_requires_normalized_failure_code(self) -> None:
        call = create_call_request(
            conversation_id=self.conversation.id,
            initiator=self.owner,
        ).call_session
        transition_call(call_session_id=call.id, target_status=CallStatus.RINGING)
        transition_call(call_session_id=call.id, target_status=CallStatus.ACCEPTED)
        with self.assertRaises(CallInvalidTransition):
            transition_call(call_session_id=call.id, target_status=CallStatus.FAILED)
        with self.assertRaises(CallInvalidTransition):
            transition_call(
                call_session_id=call.id,
                target_status=CallStatus.FAILED,
                failure_code="turn unavailable",
            )
        failed = transition_call(
            call_session_id=call.id,
            target_status=CallStatus.FAILED,
            failure_code="TURN_UNAVAILABLE",
        )
        self.assertEqual(failed.failure_code, "TURN_UNAVAILABLE")
