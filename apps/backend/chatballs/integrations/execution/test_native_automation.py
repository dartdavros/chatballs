"""Automatic native effects retain the existing explicit automation delegate."""

from chatballs.conversations.comment_models import ConversationComment
from chatballs.integrations.execution.automation import launch_automatic
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.execution.test_ai_bridge import AgentExecutionCase
from chatballs.integrations.scenario_state.automation import ScenarioAutomation
from chatballs.tenancy.database import tenant_atomic


class NativeAutomationTests(AgentExecutionCase):
    def pump(self, run):
        for _ in range(16):
            run_one(self.tenant, run.public_id, registry=self.registry)
            if self.state(run) in {"completed", "failed"}:
                return self.state(run)
        self.fail("Automatic run did not finish")

    def test_mixed_native_automation_keeps_source_author_and_rechecks_its_grant(self):
        trigger = {"id": "api", "kind": "api"}
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["triggers"] = [trigger]
            document["access"]["delegated"] = True
            document["steps"].append({"id": "native", "kind": "action", "connection": "chatballs",
                "target": "chatballs:comments.post", "inputs": {
                    "conversation_id": {"source": "context", "path": "conversation.id"},
                    "text": {"source": "constant", "value": "Automatic internal note"}}})
            self.scenario.definition = document
            self.scenario.save()
            grant = ScenarioAutomation.objects.create(scenario=self.scenario, delegate=self.tenant.membership)
        run, _ = launch_automatic(self.tenant, self.scenario, trigger, key="native-auto",
            conversation_id=self.conversation.pk, registry=self.registry)
        self.assertEqual(self.pump(run), "completed")
        run_one(self.tenant, run.public_id, registry=self.registry)
        with tenant_atomic(self.tenant):
            self.assertNotIn("ai", run.definition)
            comment = ConversationComment.objects.get()
            self.assertEqual((comment.author_id, comment.audience), (self.owner.pk, "INTERNAL"))
            self.assertEqual(len(self.calls), 1)
        denied, _ = launch_automatic(self.tenant, self.scenario, trigger, key="native-auto-revoked",
            conversation_id=self.conversation.pk, registry=self.registry)
        with tenant_atomic(self.tenant):
            grant.delegate = None
            grant.save(update_fields=["delegate"])
        self.assertEqual(self.pump(denied), "failed")
        with tenant_atomic(self.tenant):
            self.assertEqual(ConversationComment.objects.count(), 1)
            self.assertEqual(len(self.calls), 1)
