"""Native assignment keeps version, policy, history and event idempotency."""

from chatballs.conversations.assignment_policy import assignment_settings
from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.conversations.domain_event_models import ConversationEvent
from chatballs.conversations.transfer_models import ConversationTransfer
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.runner import run_one
from chatballs.tenancy.database import tenant_atomic


class NativeTransferTests(CommentTransactionTestBase):
    def setUp(self):
        super().setUp()
        self.user = HumanUser.objects.create_user(email="recipient@native-transfer.test")
        self.member = OrganizationMembership.objects.create(organization=self.organization,
            user=self.user, role="EMPLOYEE")
        with tenant_atomic(self.context):
            assignment_settings(self.context, {code: True for code in ("READY", "BUSY", "BREAK", "UNAVAILABLE")})
        run, output = execute_action(self.context, "transfers.reasons.post", {"name": "Consultation"})
        self.assertEqual(run.state, "completed")
        self.reason_id = output["reason"]["id"]

    def assign(self):
        with tenant_atomic(self.context):
            self.conversation.refresh_from_db()
        return execute_action(self.context, "conversations.assignee.post", {
            "userId": self.user.pk, "expectedVersion": self.conversation.assignment_version,
            "reasonId": self.reason_id, "comment": "Internal transfer discussion"},
            conversation_id=self.conversation.pk)

    def test_transfer_replay_preserves_single_fact_and_historical_reason(self):
        run, output = self.assign()
        self.assertEqual(run.state, "completed")
        transfer_id = output["transfer"]["id"]
        run_one(self.context, run.public_id)
        run, _ = execute_action(self.context, "transfers.reason.patch",
            {"reason_id": self.reason_id, "name": "Renamed reason"})
        self.assertEqual(run.state, "completed")
        run, output = execute_action(self.context, "transfers.history.get", {"transfer_id": transfer_id},
            conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["transfer"]["reason"]["name"], "Consultation")
        self.assertEqual(output["transfer"]["reason"]["currentName"], "Renamed reason")
        with tenant_atomic(self.context):
            self.assertEqual(ConversationTransfer.objects.filter(conversation=self.conversation).count(), 1)
            self.assertEqual(ConversationEvent.objects.filter(conversation=self.conversation,
                event_type="ASSIGNED").count(), 1)

    def test_unavailable_recipient_policy_rolls_back_assignment_and_journal(self):
        run, _ = execute_action(self.context, "conversations.assignment_policy.put",
            {code: False for code in ("READY", "BUSY", "BREAK", "UNAVAILABLE")})
        self.assertEqual(run.state, "completed")
        run, _ = self.assign()
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            self.conversation.refresh_from_db()
            self.assertIsNone(self.conversation.assigned_operator_id)
            self.assertFalse(ConversationTransfer.objects.filter(conversation=self.conversation).exists())
            self.assertFalse(ConversationEvent.objects.filter(conversation=self.conversation).exists())
