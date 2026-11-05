"""Service actions retain tenant permissions, audit, access secrecy and replay."""

import json

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.models import AuditEvent, HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt
from chatballs.integrations.service_connections.binding import load_credentials
from chatballs.integrations.service_connections.services import save_new_connection
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeServiceTests(CommentTransactionTestBase):
    secret = "NativeServiceSecretNeverReturned42"

    def connection(self, context=None, name="Service"):
        context = context or self.context
        adapter = default_registry().adapter("bitrix24")
        return save_new_connection(context=context, adapter=adapter, method=adapter.auth_method("webhook"),
            name=name, settings={}, credentials={"url": f"https://native.bitrix24.ru/rest/1/{self.secret}/"}, checked=False)

    def execute(self, key, values, *, tenant=None, state="completed"):
        run, result = execute_action(tenant or self.context, key, values)
        self.assertEqual(run.state, state, run.steps.get().error_code)
        return run, result

    def test_read_update_pause_and_delete_keep_secrets_out_and_do_not_replay(self):
        row = self.connection()
        run, result = self.execute("services.detail.get", {"connection_id": row.pk})
        self.assertTrue(result["connection"]["hasCredentials"])
        self.assertEqual(result["connection"]["host"], "native.bitrix24.ru")
        with tenant_atomic(self.context):
            receipt = NativeEffectReceipt.objects.get(step__run=run).definition
            journal = run_payload(run, detail=True, tenant=self.context)
        for payload in (result, receipt, journal):
            self.assertNotIn(self.secret, json.dumps(payload))
        run, result = self.execute("services.detail.patch", {
            "connection_id": row.pk, "name": "Renamed", "isActive": False})
        self.assertFalse(result["connection"]["isActive"])
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(AuditEvent.objects.filter(action="integrations.service_paused").count(), 1)
            self.assertEqual(AuditEvent.objects.filter(action="integrations.service_renamed").count(), 1)
        _, result = self.execute("services.get", {})
        self.assertEqual(result["items"][0]["name"], "Renamed")
        self.execute("services.detail.delete", {"connection_id": row.pk})
        with tenant_atomic(self.context):
            self.assertFalse(Integration.objects.filter(pk=row.pk).exists())
            self.assertEqual(AuditEvent.objects.filter(action="integrations.service_deleted").count(), 1)

    def test_invalid_access_and_incompatible_check_fail_without_network_or_secret_output(self):
        row = self.connection()
        self.execute("services.post", {"name": "Invalid", "adapter": "bitrix24",
            "authMethod": "webhook", "values": {"url": "invalid"}}, state="failed")
        run, _ = self.execute("services.access.post", {
            "connection_id": row.pk, "values": {"url": "invalid"}}, state="failed")
        with tenant_atomic(self.context):
            self.assertIn(self.secret, load_credentials(row.service_settings)["url"])
            journal = run_payload(run, detail=True, tenant=self.context)
            self.assertEqual(journal["steps"][0]["arguments"]["values"], {"redacted": True})
            row.service_settings.adapter_version += 1
            row.service_settings.save(update_fields=["adapter_version"])
        self.execute("services.check.post", {"connection_id": row.pk}, state="failed")
        with tenant_atomic(self.context):
            self.assertEqual(AuditEvent.objects.filter(action="integrations.service_checked", payload__ok=False).count(), 1)
            self.assertEqual(Integration.objects.filter(provider="ADAPTER").count(), 1)

    def test_catalog_and_foreign_or_employee_permissions(self):
        _, result = self.execute("services.adapters.get", {})
        self.assertEqual(result["items"][0]["key"], "bitrix24")
        row = self.connection()
        with tenant_atomic(self.context):
            user = HumanUser.objects.create_user(email="native-services-employee@example.test")
            membership = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
            ActionGrant.objects.create(organization=self.organization, membership=membership,
                native_key="services.detail.patch", scope="organization")
        self.execute("services.detail.patch", {"connection_id": row.pk, "name": "Forbidden"},
            tenant=TenantContext.for_membership(membership), state="failed")
        foreign = TenantContext.for_membership(self.foreign_author.memberships.get(organization=self.foreign))
        other = self.connection(foreign, "Foreign")
        self.execute("services.detail.get", {"connection_id": other.pk}, state="failed")
        self.execute("services.detail.delete", {"connection_id": other.pk}, state="failed")
        with tenant_atomic(self.context):
            self.assertEqual(Integration.objects.get(pk=row.pk).name, "Service")

