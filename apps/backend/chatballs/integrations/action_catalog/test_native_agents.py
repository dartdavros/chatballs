"""Agent actions use the ordinary domain policies and durable runner results."""

import json

from chatballs.ai.agent_card_commands import create
from chatballs.ai.models import AIAgent
from chatballs.channels.models import Channel
from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.models import AuditEvent, HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeAgentTests(CommentTransactionTestBase):
    def test_model_limits_survive_and_credentials_never_enter_receipts_or_journal(self):
        with tenant_atomic(self.context):
            identifier = create(self.context, {"name": "Configured"})["agent"]["id"]
            AIAgent.objects.filter(channel_id=identifier).update(model_params={
                "max_tokens": 1200, "max_completion_tokens": 800,
                "password": "ModelPasswordMustNotEscape", "note": "StoredCredentialMustNotEscape"})
            server = Integration(organization=self.organization, kind="EXTERNAL_SERVER",
                provider="MCP", name="Diagnostic server",
                last_error="password=UnstoredPasswordMustNotEscape Bearer UnstoredTokenMustNotEscape")
            server.secret = "StoredCredentialMustNotEscape"
            server.save()
        run, output = execute_action(self.context, "agents.detail.get", {"agent_id": identifier})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["agent"]["modelParams"]["max_tokens"], 1200)
        with tenant_atomic(self.context):
            receipt = NativeEffectReceipt.objects.get(step__run=run).definition
            journal = run_payload(run, detail=True, tenant=self.context)
        self.assertEqual(journal["steps"][0]["result"]["agent"]["modelParams"]["max_completion_tokens"], 800)
        for document in (output, receipt, journal):
            content = json.dumps(document)
            for secret in ("ModelPasswordMustNotEscape", "StoredCredentialMustNotEscape",
                    "UnstoredPasswordMustNotEscape", "UnstoredTokenMustNotEscape"):
                self.assertNotIn(secret, content)

    def test_create_update_read_and_delete_preserve_audit_and_do_not_replay(self):
        run, output = execute_action(self.context, "agents.post", {"name": "Scenario agent"})
        self.assertEqual(run.state, "completed")
        identifier = output["agent"]["id"]
        self.assertEqual(output["agent"]["aiStatus"], "DRAFT")
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(Channel.objects.filter(name="Scenario agent").count(), 1)
            self.assertEqual(AuditEvent.objects.filter(action="ai.agent_created").count(), 1)
        run, output = execute_action(self.context, "agents.detail.patch", {
            "agent_id": identifier, "name": "Updated agent", "answerLanguage": "en", "transcriptionLanguage": "en-US",
            "synthesisIntegrationId": None, "synthesisModel": "general", "synthesisVoice": "john"})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["agent"]["answerLanguage"], "en")
        self.assertEqual(output["agent"]["transcriptionLanguage"], "en-US")
        self.assertEqual(output["agent"]["synthesisVoice"], "john")
        self.assertEqual(output["agent"]["synthesisModel"], "general")
        for key in ("agents.get", "agents.directory.get"):
            run, output = execute_action(self.context, key, {"q": "Updated agent"})
            self.assertEqual(run.state, "completed")
            self.assertEqual([row["id"] for row in output["items"]], [identifier])
        run, output = execute_action(self.context, "agents.detail.get", {"agent_id": identifier})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["agent"]["name"], "Updated agent")
        run, _ = execute_action(self.context, "agents.detail.delete", {"agent_id": identifier})
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.context):
            self.assertFalse(Channel.objects.filter(pk=identifier).exists())
            self.assertEqual(AuditEvent.objects.get(action="ai.agent_deleted").object_id, str(identifier))

    def test_connection_binding_is_tenant_scoped_and_grants_do_not_elevate_employee(self):
        with tenant_atomic(self.context):
            own = create(self.context, {"name": "Own"})["agent"]["id"]
            connection = Integration.objects.create(organization=self.organization,
                kind="MESSENGER", provider="TELEGRAM", name="Transport")
            user = HumanUser.objects.create_user(email="agent-operator@example.test")
            member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
            ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="agents.detail.patch", scope="organization")
        foreign_context = TenantContext.for_membership(self.foreign_author.memberships.get(organization=self.foreign))
        with tenant_atomic(foreign_context):
            foreign = create(foreign_context, {"name": "Foreign"})["agent"]["id"]
        run, _ = execute_action(self.context, "agents.detail.patch", {"agent_id": foreign, "name": "Forbidden"})
        self.assertEqual(run.state, "failed")
        run, _ = execute_action(TenantContext.for_membership(member), "agents.detail.patch", {
            "agent_id": own, "name": "Forbidden"})
        self.assertEqual(run.state, "failed")
        run, output = execute_action(self.context, "agents.connections.post", {
            "agent_id": own, "integrationId": connection.pk})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["agent"]["connections"][0]["id"], connection.pk)
        run, _ = execute_action(self.context, "agents.connection.delete", {
            "agent_id": own, "integration_id": connection.pk})
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.context):
            connection.refresh_from_db()
            self.assertIsNone(connection.channel_id)
            self.assertEqual(Channel.objects.get(pk=own).name, "Own")

    def test_test_chat_unconfigured_agent_returns_failure_without_provider_diagnostics(self):
        with tenant_atomic(self.context):
            identifier = create(self.context, {"name": "Draft"})["agent"]["id"]
        run, output = execute_action(self.context, "agents.test_chat.post", {
            "agent_id": identifier, "message": "Hello"})
        self.assertEqual(run.state, "failed")
        self.assertFalse(output)
