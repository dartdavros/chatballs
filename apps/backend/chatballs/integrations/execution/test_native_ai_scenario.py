"""AI scenario grants use the same runner for service and native steps."""

from chatballs.conversations.comment_models import ConversationComment
from chatballs.integrations.execution.ai_launch import launch_ai
from chatballs.integrations.execution.ai_policy import bind
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.execution.scenario_agent_policies import save as save_policies
from chatballs.integrations.execution.test_ai_bridge import AgentExecutionCase
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant
from chatballs.tenancy.database import tenant_atomic


class NativeAIScenarioTests(AgentExecutionCase):
    def configure(self):
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["triggers"] = [{"id": "agent", "kind": "ai", "agents": [self.agent.pk]}]
            document["steps"].append({"id": "native", "kind": "action", "connection": "chatballs",
                "target": "chatballs:comments.post", "inputs": {
                    "conversation_id": {"source": "constant", "value": str(self.conversation.pk)},
                    "text": {"source": "constant", "value": "Mixed AI sequence"}}})
            self.scenario.definition = document
            self.scenario.save()
            save_policies(self.tenant, self.scenario, [{"agent": self.agent.pk, "mode": "self", "revision": 0}])
            grant = AgentActionGrant.objects.get(agent=self.agent, scenario=self.scenario)
            self.assertEqual(grant.delegate_id, self.tenant.membership_id)
            return grant

    def test_mixed_ai_steps_keep_explicit_delegate_and_original_services(self):
        grant = self.configure()
        run = launch_ai(self.tenant, bind(grant, self.conversation), {}, "mixed", registry=self.registry)
        for _ in range(12):
            run_one(self.tenant, run.public_id, registry=self.registry)
            if self.state(run) in {"completed", "failed"}:
                break
        with tenant_atomic(self.tenant):
            self.assertEqual(self.state(run), "completed")
            self.assertEqual(len(self.calls), 1)
            self.assertEqual(ConversationComment.objects.get().author_id, self.owner.pk)
            self.assertEqual(set(run.steps.values_list("adapter_key", flat=True)), {"bitrix24", "chatballs"})

    def test_existing_scenario_mode_never_infers_delegate_after_native_is_added(self):
        grant = self.configure()
        with tenant_atomic(self.tenant):
            grant.delegate = None
            grant.save(update_fields=["delegate"])
            save_policies(self.tenant, self.scenario,
                [{"agent": self.agent.pk, "mode": "self", "revision": grant.revision}])
            grant.refresh_from_db()
            self.assertIsNone(grant.delegate_id)
        with self.assertRaises(ExecutionDenied):
            launch_ai(self.tenant, bind(grant, self.conversation), {}, "legacy", registry=self.registry)
