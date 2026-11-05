"""Native AI checks use real tenant/domain services and the shared runner."""

from unittest.mock import patch

from chatballs.ai.models import AIAgent
from chatballs.integrations.action_catalog.native_file_test_base import NativeFileCase
from chatballs.integrations.execution.agent_actions import change_policy
from chatballs.integrations.execution.ai_bridge import plan_actions
from chatballs.integrations.execution.ai_launch import launch_ai
from chatballs.integrations.execution.ai_policy import bind
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant
from chatballs.tenancy.database import tenant_atomic


class NativeAICase(NativeFileCase):
    def setUp(self):
        super().setUp()
        with tenant_atomic(self.context):
            channel = self.conversation.channel
            provider = Integration.objects.create(organization=self.organization, name="Provider",
                kind="LLM_PROVIDER", provider="DEMO", secret="test-provider", is_active=True)
            self.agent = AIAgent.objects.create(channel=channel, provider_integration=provider,
                status="ACTIVE", model="test")
            self.connection.channel = channel
            self.connection.save(update_fields=["channel"])
            self.conversation.assigned_operator = None
            self.conversation.save(update_fields=["assigned_operator"])
            change_policy(self.context, self.agent, "native:comments.post", "self", 0)
            self.grant = AgentActionGrant.objects.get(agent=self.agent, native_key="comments.post")
            self.binding = bind(self.grant, self.conversation)

    def start(self, *, key="native-ai", arguments=None):
        return launch_ai(self.context, self.binding, arguments or {"text": "Private discussion"}, key)

    def tools(self):
        with tenant_atomic(self.context), patch(
                "chatballs.integrations.execution.ai_bridge.cached_tool_support", return_value=True):
            return plan_actions(self.agent, self.conversation)

    def execute(self, run):
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            run.refresh_from_db()
            self.assertEqual(run.state, "completed", run.steps.get().error_code)

