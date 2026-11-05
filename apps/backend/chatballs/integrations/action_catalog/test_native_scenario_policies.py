"""Native settings preserve current delegates, atomic revisions and scope."""

from chatballs.ai.models import AIAgent
from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.models import Integration, ServiceConnectionSettings
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant
from chatballs.integrations.scenario_state.synchronization import ServiceSynchronizationSettings
from chatballs.tenancy.database import tenant_atomic


class NativeScenarioPolicyTests(CommentTransactionTestBase):
    def execute(self, key, values, *, state="completed"):
        run, result = execute_action(self.context, key, values)
        self.assertEqual(run.state, state, run.steps.get().error_code)
        return result

    def test_agent_policy_is_explicit_revisioned_atomic_and_captures_actual_delegate(self):
        with tenant_atomic(self.context):
            provider = Integration.objects.create(organization=self.organization, name="Provider", kind="LLM_PROVIDER", provider="DEMO")
            agent = AIAgent.objects.create(channel=self.conversation.channel, provider_integration=provider, status="ACTIVE", model="test")
        channel = self.conversation.channel_id
        result = self.execute("agents.actions.get", {"channel_id": channel})
        item = next(row for row in result["items"] if row["id"] == "native:groups.get")
        self.assertEqual(item["mode"], "off")
        self.execute("agents.actions.put", {"channel_id": channel, "items": [{"id": item["id"], "mode": "ask", "revision": 0}]})
        with tenant_atomic(self.context):
            grant = AgentActionGrant.objects.get(agent=agent, native_key="groups.get")
            self.assertEqual(grant.delegate_id, self.context.membership_id)
            revision = grant.revision
        self.execute("agents.actions.put", {"channel_id": channel, "items": [
            {"id": item["id"], "mode": "self", "revision": revision},
            {"id": "native:groups.post", "mode": "self", "revision": 99}]}, state="failed")
        with tenant_atomic(self.context):
            grant.refresh_from_db()
            self.assertEqual(grant.mode, "ask")
        self.execute("agents.actions.put", {"channel_id": channel, "items": [{"id": item["id"], "mode": "off", "revision": revision}]})

    def test_synchronization_keeps_supported_direction_revision_and_captured_actor(self):
        with tenant_atomic(self.context):
            connection = Integration.objects.create(organization=self.organization, name="CRM", kind="SERVICE", provider="ADAPTER")
            ServiceConnectionSettings.objects.create(organization=self.organization, integration=connection,
                adapter_key="bitrix24", adapter_version=1, auth_method="webhook")
        self.assertEqual(self.execute("synchronization.get", {"connection_id": connection.pk})["revision"], 0)
        pair = {"id": "contact", "enabled": True, "left": {"connection": "chatballs", "entity": "contact"},
            "right": {"connection": str(connection.pk), "entity": "contact"}, "direction": "both",
            "fields": [{"left": "name", "right": "NAME", "direction": "reverse"}], "sourceOfTruth": "latest",
            "conflict": "manual", "deletion": "unlink", "causality": {"suppressEcho": True, "requireExplicitLink": True}}
        data = {"connection_id": connection.pk, "revision": 0, "definition": {"version": 1, "synchronization": [pair]}}
        self.execute("synchronization.put", data, state="failed")
        pair["direction"] = "reverse"
        result = self.execute("synchronization.put", data)
        self.assertEqual(result["revision"], 1)
        self.execute("synchronization.put", data, state="failed")
        with tenant_atomic(self.context):
            row = ServiceSynchronizationSettings.objects.get(integration=connection)
            self.assertEqual(row.delegate_id, self.context.membership_id)
