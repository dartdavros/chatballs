"""Organization commands retain operating modes, tenancy, and secret boundaries."""

import json

from django.utils.translation import override

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.demo_models import DemoDataset
from chatballs.identity.demo_seed import manifest
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeSettingsTests(CommentTransactionTestBase):
    def test_mode_change_uses_existing_queue_transition_and_onboarding_is_personal(self):
        with tenant_atomic(self.context):
            self.conversation.control_mode = "AI"
            self.conversation.save(update_fields=["control_mode"])
        run, output = execute_action(self.context, "settings.patch", {"operationMode": "OPERATORS_ONLY"})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["organization"]["operationMode"], "OPERATORS_ONLY")
        with tenant_atomic(self.context):
            self.conversation.refresh_from_db()
            self.assertEqual(self.conversation.control_mode, "PAUSED")
            self.assertEqual(self.conversation.expected_responder, "OPERATOR")
        run, output = execute_action(self.context, "settings.get", {})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["organization"]["operationMode"], "OPERATORS_ONLY")
        run, output = execute_action(self.context, "settings.onboarding.post", {"action": "complete"})
        self.assertEqual(run.state, "completed")
        self.assertIsNotNone(output["completedAt"])
        self.assertEqual(output["completedAt"], output["dismissedAt"])

    def test_audit_and_demo_credentials_are_removed_before_receipts(self):
        with tenant_atomic(self.context):
            self.author.ui_language = "en"
            self.author.save(update_fields=["ui_language"])
            integration = Integration(organization=self.organization, kind="LLM_PROVIDER", provider="DEMO", name="Demo")
            integration.secret = "AuditConnectionCredential42"
            integration.save()
            record_audit_event(organization=self.organization, actor=self.author, action="identity.employee_created",
                payload={"nested": {"password": "NeverExpose42"}, "note": "AuditConnectionCredential42", "count": 3})
            DemoDataset.objects.create(organization=self.organization, status="INSTALLED",
                error="password=StorageCredentialMustNotEscape")
        with override("ru"):
            run, output = execute_action(self.context, "settings.audit.get", {"category": "identity"})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["items"][0]["categoryLabel"], t("audit.category_identity", language="en"))
        with tenant_atomic(self.context):
            content = json.dumps(NativeEffectReceipt.objects.get(step__run=run).definition)
            self.assertNotIn("NeverExpose42", content)
            self.assertNotIn("AuditConnectionCredential42", content)
        self.assertEqual(output["items"][0]["details"]["count"], 3)
        run, output = execute_action(self.context, "settings.demo.get", {})
        self.assertEqual(run.state, "completed")
        self.assertTrue(output["accounts"])
        self.assertTrue(all("password" not in row for row in output["accounts"]))
        with tenant_atomic(self.context):
            content = json.dumps(NativeEffectReceipt.objects.get(step__run=run).definition)
            self.assertNotIn(manifest.load("organization", "ru")["demoPassword"], content)
            self.assertNotIn("StorageCredentialMustNotEscape", content)
        self.assertEqual(output["error"], t("native.settings.demo_status.FAILED", language="en"))

    def test_communication_rolls_back_foreign_item_and_grants_do_not_override_settings_policy(self):
        with tenant_atomic(self.context):
            row = Integration.objects.create(organization=self.organization, kind="MESSENGER", provider="TELEGRAM", name="Own", voice_messages_enabled=False)
            user = HumanUser.objects.create_user(email="settings-employee@example.test")
            member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
            ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="settings.patch", scope="organization")
        with tenant_atomic(TenantContext.for_resource(self.foreign)):
            foreign = Integration.objects.create(organization=self.foreign, kind="MESSENGER", provider="TELEGRAM", name="Foreign")
        run, _ = execute_action(self.context, "settings.communication.patch", {"items": [
            {"id": row.pk, "voiceMessages": True}, {"id": foreign.pk, "voiceMessages": True}]})
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            row.refresh_from_db()
            self.assertFalse(row.voice_messages_enabled)
        run, output = execute_action(self.context, "settings.communication.patch", {"items": [{"id": row.pk, "voiceMessages": True}]})
        self.assertEqual(run.state, "completed")
        self.assertTrue(output["items"][0]["voiceMessages"])
        run, _ = execute_action(TenantContext.for_membership(member), "settings.patch", {"name": "Forbidden"})
        self.assertEqual(run.state, "failed")
        self.organization.refresh_from_db()
        self.assertNotEqual(self.organization.name, "Forbidden")
