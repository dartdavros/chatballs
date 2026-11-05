"""Native connection permissions, write semantics, receipts and secret boundaries."""

import json

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.models import AuditEvent, HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.models import Integration, ToolReadOnlyConfirmation
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeConnectionTests(CommentTransactionTestBase):
    secret = "NativeProviderCredential42"

    def execute(self, key, values, *, tenant=None, state="completed"):
        run, result = execute_action(tenant or self.context, key, values)
        self.assertEqual(run.state, state, run.steps.get().error_code)
        return run, result

    def create(self):
        return self.execute("connections.post", {"provider": "CUSTOM", "name": "Native provider",
            "secret": self.secret, "config": {"baseUrl": "https://api.example.test/v1", "defaultModel": "model",
                "proxyUrl": "socks5://operator:ProxyCredential42@proxy.example.test:1080"}})

    def test_create_edit_list_delete_preserve_secrets_and_single_audit(self):
        run, output = self.create()
        identifier = output["integration"]["id"]
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(AuditEvent.objects.filter(action="integrations.integration_created").count(), 1)
            row = Integration.objects.get(pk=identifier)
            self.assertEqual(row.secret, self.secret)
            row.last_error = f"Bearer UnstoredSecret42 password=OtherPassword42 {self.secret}"
            row.save(update_fields=["last_error"])
        _, output = self.execute("connections.detail.patch", {"integration_id": identifier,
            "name": "Renamed", "isActive": False, "config": {"baseUrl": "https://api.example.test/v1",
                "defaultModel": "next-model", "proxyUrl": "socks5://operator:••••••••@proxy.example.test:1080"}})
        self.assertFalse(output["integration"]["isActive"])
        with tenant_atomic(self.context):
            row.refresh_from_db()
            self.assertEqual(row.secret, self.secret)
            self.assertIn("ProxyCredential42", row.config["proxy_url"])
            row.last_error = f"Bearer UnstoredSecret42 password=OtherPassword42 {self.secret}"
            row.save(update_fields=["last_error"])
        run, output = self.execute("connections.get", {})
        with tenant_atomic(self.context):
            receipt = NativeEffectReceipt.objects.get(step__run=run).definition
        for payload in (output, receipt):
            serialized = json.dumps(payload)
            for secret in (self.secret, "ProxyCredential42", "UnstoredSecret42", "OtherPassword42"):
                self.assertNotIn(secret, serialized)
        self.execute("connections.detail.delete", {"integration_id": identifier})
        with tenant_atomic(self.context):
            self.assertFalse(Integration.objects.filter(pk=identifier).exists())

    def test_tool_confirmation_requires_explicit_mark_and_keeps_actor_and_revoke(self):
        with tenant_atomic(self.context):
            row = Integration.objects.create(organization=self.organization, provider="MCP", kind="EXTERNAL_SERVER",
                name="Server", config={"url": "https://example.test"},
                tools=[{"name": "lookup", "read_only_hint": False, "input_schema": {"type": "object"}}])
        values = {"integration_id": row.pk, "name": "lookup"}
        self.execute("connections.tools.confirm.post", {**values, "confirmed": False}, state="failed")
        self.execute("connections.tools.confirm.post", {**values, "confirmed": True})
        with tenant_atomic(self.context):
            confirmation = ToolReadOnlyConfirmation.objects.get(integration=row)
            self.assertEqual(confirmation.confirmed_by_id, self.context.actor_user.pk)
        self.execute("connections.tools.revoke.post", values)
        with tenant_atomic(self.context):
            confirmation.refresh_from_db()
            self.assertIsNotNone(confirmation.revoked_at)
        _, result = self.execute("connections.address.post", {"url": "file:///etc/passwd"})
        self.assertTrue(result["errors"])

    def test_grant_cannot_expand_scope_product_permission_or_tenant(self):
        _, result = self.create()
        identifier = result["integration"]["id"]
        with tenant_atomic(self.context):
            user = HumanUser.objects.create_user(email="native-connection-employee@example.test")
            member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
            grant = ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="connections.detail.patch", scope="contact")
        employee = TenantContext.for_membership(member)
        with self.assertRaises(ExecutionDenied):
            self.execute("connections.detail.patch", {"integration_id": identifier}, tenant=employee)
        with tenant_atomic(self.context):
            grant.scope = "organization"
            grant.save(update_fields=["scope"])
        self.execute("connections.detail.patch", {"integration_id": identifier, "name": "Forbidden"}, tenant=employee, state="failed")
        foreign = TenantContext.for_membership(self.foreign_author.memberships.get(organization=self.foreign))
        self.execute("connections.detail.delete", {"integration_id": identifier}, tenant=foreign, state="failed")
        self.execute("connections.post", {"provider": "CUSTOM", "name": "Missing key",
            "config": {"baseUrl": "https://api.example.test", "defaultModel": "model"}}, state="failed")
        with tenant_atomic(self.context):
            self.assertEqual(Integration.objects.get(pk=identifier).name, "Native provider")
