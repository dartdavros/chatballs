"""Use historical models on both sides; preserve existing settings, history and secrets."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ExternalMigrationTests(TransactionTestCase):
    def test_additive_migration_preserves_builtin_agents(self):
        executor = MigrationExecutor(connection)
        current = executor.loader.graph.leaf_nodes()
        previous = [("ai", "0031_aiagent_synthesis"), ("identity", "0048_organization_operation_mode"),
                    ("tenancy", "0080_site_event_guards"), ("integrations", "0035_integration_openai_provider")]
        executor.migrate(previous)
        try:
            apps = executor.loader.project_state(previous).apps
            organization = apps.get_model("identity", "Organization").objects.create(name="Existing", slug="external-migration")
            channel = apps.get_model("channels", "Channel").objects.create(organization=organization, name="Existing", code="existing")
            integration = apps.get_model("integrations", "Integration").objects.create(
                organization=organization, name="Existing provider", kind="LLM_PROVIDER", provider="OPENAI",
                secret="preserved-provider-secret", config={"default_model": "existing-model"},
            )
            agent = apps.get_model("ai", "AIAgent").objects.create(
                organization=organization, channel=channel, name="Agent", provider_integration=integration,
                model="explicit-model", allowed_tools=["existing-tool"], persona="Existing instructions",
            )
            contact = apps.get_model("conversations", "Contact").objects.create(organization=organization, name="Existing")
            conversation = apps.get_model("conversations", "Conversation").objects.create(organization=organization, channel=channel, contact=contact)
            message = apps.get_model("conversations", "Message").objects.create(
                organization=organization, conversation=conversation, author_type="CONTACT", text="Existing history")
            identifiers = organization.pk, agent.pk, integration.pk, conversation.pk, message.pk
        finally:
            MigrationExecutor(connection).migrate(current)
        apps = MigrationExecutor(connection).loader.project_state(current).apps
        organization_id, agent_id, integration_id, conversation_id, message_id = identifiers
        organization = apps.get_model("identity", "Organization").objects.get(pk=organization_id)
        agent = apps.get_model("ai", "AIAgent").objects.get(pk=agent_id)
        integration = apps.get_model("integrations", "Integration").objects.get(pk=integration_id)
        self.assertFalse(organization.external_execution_enabled)
        self.assertEqual(agent.execution_mode, "builtin")
        self.assertEqual((agent.provider_integration_id, agent.model, agent.allowed_tools, agent.persona),
                         (integration_id, "explicit-model", ["existing-tool"], "Existing instructions"))
        self.assertEqual(integration.secret, "preserved-provider-secret")
        self.assertEqual(integration.provider, "OPENAI")
        self.assertEqual(apps.get_model("conversations", "Message").objects.get(pk=message_id).text, "Existing history")
        self.assertTrue(apps.get_model("conversations", "Conversation").objects.filter(pk=conversation_id).exists())
        for name in ("ExternalAgentConnection", "ExternalAgentBinding", "ExternalAgentSession"):
            self.assertEqual(apps.get_model("ai", name).objects.count(), 0)
