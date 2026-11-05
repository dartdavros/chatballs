"""Rule updates preserve synchronization, source validation and single versioning."""

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.conversations.queue_models import QueueEscalationPolicy
from chatballs.conversations.rules.models import HandlingRule
from chatballs.conversations.rules.operations import list_rules
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.runner import run_one
from chatballs.tenancy.database import tenant_atomic


class NativeRuleTests(CommentTransactionTestBase):
    def test_queue_deadline_and_return_rule_stay_synchronized_once(self):
        run, output = execute_action(self.context, "conversations.queue_policy.patch",
            {"assignment_timeout_minutes": 23})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["assignment_timeout_minutes"], 23)
        with tenant_atomic(self.context):
            rule = HandlingRule.objects.get(organization=self.organization, kind="ASSIGNMENT_RETURN")
            version = rule.version
            self.assertEqual(rule.delay_minutes, 23)
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            rule.refresh_from_db()
            self.assertEqual(rule.version, version)
            self.assertEqual(QueueEscalationPolicy.objects.get(organization=self.organization).assignment_timeout_minutes, 23)

    def test_foreign_channel_condition_cannot_change_rule_or_version(self):
        with tenant_atomic(self.context):
            list_rules(self.context)
            rule = HandlingRule.objects.get(organization=self.organization, kind="WAIT_EXCEEDED_NOTICE")
            before = (rule.version, rule.conditions)
        run, _ = execute_action(self.context, "rules.rule.patch", {"kind": "WAIT_EXCEEDED_NOTICE",
            "conditions": {"channelIds": [self.foreign_conversation.channel_id]}})
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            rule.refresh_from_db()
            self.assertEqual((rule.version, rule.conditions), before)
