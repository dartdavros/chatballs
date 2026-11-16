import secrets

from django.db import IntegrityError, connection, transaction
from django.test import TransactionTestCase

from chatballs.ai.external_agents.auth import authenticated, key_hash
from chatballs.ai.external_agents.config_models import ExternalAgentConnection
from chatballs.identity.models import Organization
from chatballs.integrations.models import Integration, ServiceConnectionSettings
from chatballs.tenancy.database import tenant_atomic


class ExternalIsolationTests(TransactionTestCase):
    def setUp(self):
        self.first = Organization.objects.create(name="First", slug="external-rls-first", external_execution_enabled=True)
        self.second = Organization.objects.create(name="Second", slug="external-rls-second", external_execution_enabled=True)
        self.key = secrets.token_urlsafe(48)
        self.connection = self.create_connection(self.first, self.key)
        self.foreign = self.create_connection(self.second, secrets.token_urlsafe(48))

    def create_connection(self, organization, key):
        integration = Integration.objects.create(organization=organization, name="External", kind="SERVICE", provider="ADAPTER")
        ServiceConnectionSettings.objects.create(integration=integration, adapter_key="external_agent_v1", adapter_version=1,
                                                 auth_method="bearer", credentials='{"token":"outgoing"}', settings={"base_url": "https://example.invalid"})
        return ExternalAgentConnection.objects.create(integration=integration, inbound_key_hash=key_hash(key),
                                                       deduplication_key=secrets.token_urlsafe(48))

    def test_runtime_rls_and_hashed_ingress_directory(self):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
            self.assertEqual(ExternalAgentConnection.objects.count(), 0)
        with tenant_atomic(self.first.pk), connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
            self.assertEqual(list(ExternalAgentConnection.objects.values_list("pk", flat=True)), [self.connection.pk])
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
            with authenticated("Bearer " + self.key) as (context, row):
                self.assertEqual(context.organization_id, self.first.pk)
                self.assertEqual(row.pk, self.connection.pk)

    def test_database_rejects_foreign_link_and_dedup_key_mutation(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExternalAgentConnection.objects.filter(pk=self.connection.pk).update(integration=self.foreign.integration)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExternalAgentConnection.objects.filter(pk=self.connection.pk).update(deduplication_key="replacement")

    def test_credentials_change_invalidates_compatibility_and_authority_version(self):
        previous = self.connection.revision
        row = self.connection.integration.service_settings
        row.credentials = '{"token":"rotated"}'
        row.save(update_fields=["credentials"])
        self.connection.refresh_from_db()
        self.assertGreater(self.connection.revision, previous)
        self.assertIsNone(self.connection.checked_at)
