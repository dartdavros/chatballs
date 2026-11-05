"""Assistance queue, protected history and rejection through the shared runner."""

from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from chatballs.ai.assistance_generation import finish
from chatballs.ai.assistance_test_base import AssistanceTestData
from chatballs.ai.models import ReplyAssistanceAttempt, ReplySuggestion
from chatballs.conversations.models import Conversation, Message
from chatballs.events.models import OutboxEvent
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


@override_settings(CHATBALLS_AI_TURN_DEADLINE_SECONDS=3600)
class NativeAssistanceTests(AssistanceTestData, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.context = TenantContext.for_membership(self.member)
        self.agent.assistance_enabled = True
        self.agent.save(update_fields=["assistance_enabled"])

    def execute(self, key, values=None, *, context=None):
        return execute_action(context or self.context, key, values or {}, conversation_id=self.conversation.pk)

    def test_request_queues_once_and_protected_reads_return_typed_pending_work(self):
        run, data = self.execute("messages.assistance.post")
        self.assertEqual((run.state, data["suggestion"]["status"]), ("completed", "PENDING"))
        run_one(self.context, run.public_id)
        current, data = self.execute("messages.assistance_attempt.get", {"attempt_id": data["suggestion"]["attemptId"]})
        self.assertEqual((current.state, data["attempt"]["status"]), ("completed", "PENDING"))
        listed, data = self.execute("messages.assistance.get")
        self.assertEqual((listed.state, len(data["items"])), ("completed", 1))
        with tenant_atomic(self.context):
            self.assertEqual(OutboxEvent.objects.filter(event_type="conversation.reply_assistance_requested").count(), 1)
            self.assertEqual(ReplySuggestion.objects.count(), 1)
            self.assertFalse(Message.objects.exists())

    def test_rejection_preserves_generated_text_and_first_rejection_author(self):
        # An existing completed generation in the isolated test database;
        # no provider, fake API or product demonstration is created.
        with tenant_atomic(self.context):
            attempt = self.attempt()
            suggestion = self.suggestion(attempt)
            now = timezone.now()
            for operation in (attempt, suggestion):
                operation.started_at = now
                operation.status = "RUNNING"
                operation.save(update_fields=["status", "started_at"])
            finish(suggestion, text="Existing protected suggestion")
        values = {"suggestion_id": str(suggestion.public_id)}
        first, data = self.execute("messages.suggestion.post", values)
        self.assertEqual(first.state, "completed")
        self.assertEqual(data["suggestion"]["originalText"], suggestion.original_text)
        repeated, again = self.execute("messages.suggestion.post", values)
        self.assertEqual((repeated.state, again), ("completed", data))
        with tenant_atomic(self.context):
            suggestion.refresh_from_db()
            self.assertEqual(suggestion.rejected_by_id, self.member.pk)
            self.assertFalse(Message.objects.exists())

    def test_employee_grant_does_not_replace_assignment_and_foreign_attempt_is_rejected(self):
        _organization, foreign_member, _agent, _conversation = self.create_tenant("foreign-assistance")
        foreign = ReplyAssistanceAttempt.objects.create(organization=_organization, requested_by=foreign_member,
            agent=_agent, conversation=_conversation, operation_key="foreign", history_version="foreign-history")
        rejected, _ = self.execute("messages.assistance_attempt.get", {"attempt_id": str(foreign.public_id)})
        self.assertEqual(rejected.state, "failed")
        with tenant_atomic(self.context):
            user = HumanUser.objects.create_user(email="native-assistance-viewer@example.test")
            member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
            ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="messages.assistance.post", scope="conversation")
        rejected, _ = self.execute("messages.assistance.post", context=TenantContext.for_membership(member))
        self.assertEqual(rejected.state, "failed")
        with tenant_atomic(self.context):
            self.assertFalse(ReplySuggestion.objects.exists())

    def test_expiry_and_closed_conversation_keep_original_source_behavior(self):
        _run, data = self.execute("messages.assistance.post")
        with override_settings(CHATBALLS_AI_TURN_DEADLINE_SECONDS=-1):
            run, data = self.execute("messages.assistance_attempt.get", {"attempt_id": data["suggestion"]["attemptId"]})
        self.assertEqual((run.state, data["attempt"]["status"], data["attempt"]["errorCode"]),
            ("completed", "ERROR", "TIMEOUT"))
        with tenant_atomic(self.context):
            Conversation.objects.filter(pk=self.conversation.pk).update(lifecycle="CLOSED")
        rejected, _ = self.execute("messages.assistance.post")
        self.assertEqual(rejected.state, "failed")
        with tenant_atomic(self.context):
            self.assertEqual(ReplySuggestion.objects.count(), 1)
