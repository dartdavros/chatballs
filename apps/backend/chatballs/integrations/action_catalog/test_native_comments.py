"""Real PostgreSQL/domain services through the native runner boundary."""

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.db import IntegrityError, ProgrammingError, connection, transaction
from django.utils import timezone

from chatballs.conversations.comment_models import ConversationComment
from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.conversations.models import Message
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.launch import launch, launch_direct
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeCommentTests(CommentTransactionTestBase):
    def test_explicit_organization_grant_keeps_the_original_employee_role(self):
        user = HumanUser.objects.create_user(email="native-catalog@example.test")
        member = OrganizationMembership.objects.create(organization=self.organization,
            user=user, role="EMPLOYEE")
        tenant = TenantContext.for_membership(member)
        with tenant_atomic(tenant):
            ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="labels.get", operation_key="", scope="organization")
        run, _ = launch_direct(tenant=tenant, connection_id="chatballs", operation_key="labels.get",
            trigger_key="catalog", arguments={})
        run_one(tenant, run.public_id)
        with tenant_atomic(tenant):
            run.refresh_from_db()
            self.assertEqual(run.state, "completed")
            self.assertEqual(run.steps.get().definition["result"], {"items": []})
            self.assertEqual(OrganizationMembership.objects.get(pk=member.pk).role, "EMPLOYEE")

    def test_direct_preview_binds_current_conversation_and_uses_same_runner(self):
        preview, _ = launch_direct(tenant=self.context, connection_id="chatballs",
            operation_key="comments.post", trigger_key="direct-note", arguments={"text": "Direct note"},
            conversation_id=self.conversation.pk, preview=True)
        self.assertEqual(preview["arguments"]["conversation_id"], str(self.conversation.pk))
        run, _ = launch_direct(tenant=self.context, connection_id="chatballs",
            operation_key="comments.post", trigger_key="direct-note", arguments={"text": "Direct note"},
            conversation_id=self.conversation.pk, confirmation=preview["confirmation"])
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            run.refresh_from_db()
            self.assertEqual(run.state, "completed")
            self.assertEqual(ConversationComment.objects.filter(organization=self.organization).get().text, "Direct note")

    def test_operational_retention_clears_receipt_but_preserves_domain_comment(self):
        from chatballs.integrations.execution.retention import cleanup
        tenant, run = self.start()
        run_one(tenant, run.public_id)
        with tenant_atomic(tenant):
            type(run).objects.filter(pk=run.pk).update(finished_at=timezone.now() - timedelta(days=8))
        cleanup(tenant)
        with tenant_atomic(tenant):
            self.assertFalse(NativeEffectReceipt.objects.filter(organization=self.organization).exists())
            self.assertEqual(ConversationComment.objects.filter(organization=self.organization).count(), 1)

    def start(self, *, target=None, actor=None):
        tenant = actor or self.context
        with tenant_atomic(tenant):
            document = empty_definition()
            document["access"]["staff"] = [tenant.actor_user.pk]
            document["steps"] = [{"id": "comment", "kind": "action", "connection": "chatballs",
                "target": "chatballs:comments.post", "inputs": {
                    "conversation_id": {"source": "constant", "value": str((target or self.conversation).pk)},
                    "text": {"source": "constant", "value": "Staff-only discussion"}}}]
            scenario = ScenarioDefinition(organization=self.organization, name="Internal note", enabled=True)
            scenario.definition = document
            scenario.save()
        run, _ = launch(tenant=tenant, scenario_id=scenario.public_id,
            trigger_key="comment", parameters={}, conversation_id=self.conversation.pk)
        with tenant_atomic(tenant):
            digest = invocation_digest(run.steps.get(), run)
        control(tenant=tenant, public_id=run.public_id, action="approve", digest=digest)
        return tenant, run

    def test_runner_appends_internal_once_and_keeps_result_encrypted(self):
        tenant, run = self.start()
        run_one(tenant, run.public_id)
        run_one(tenant, run.public_id)
        with tenant_atomic(tenant):
            run.refresh_from_db()
            self.assertEqual(run.state, "completed")
            self.assertEqual(ConversationComment.objects.filter(organization=self.organization).count(), 1)
            self.assertFalse(Message.objects.filter(conversation=self.conversation).exists())
            comment = ConversationComment.objects.filter(organization=self.organization).get()
            self.assertEqual(comment.audience, "INTERNAL")
            receipt = NativeEffectReceipt.objects.filter(organization=self.organization).get()
            self.assertNotIn(comment.text, receipt.content)
            self.assertEqual(receipt.definition["result"]["comment"]["id"], comment.pk)
            self.assertIsNone(run.steps.get().integration_id)

    def test_foreign_target_does_not_bypass_context_or_tenant(self):
        tenant, run = self.start(target=self.foreign_conversation)
        run_one(tenant, run.public_id)
        with tenant_atomic(tenant):
            run.refresh_from_db()
            self.assertEqual(run.state, "failed")
            self.assertFalse(ConversationComment.objects.filter(organization=self.organization).exists())
            self.assertFalse(NativeEffectReceipt.objects.filter(organization=self.organization).exists())

    def test_crash_before_checkpoint_rolls_back_effect_and_retries_once(self):
        from chatballs.conversations.comment_services import create_comment
        foreign_tenant = TenantContext.for_membership(self.foreign_author.memberships.get())
        prior, _ = create_comment(context=foreign_tenant, conversation_id=self.foreign_conversation.pk,
            audience="INTERNAL", text="Another tenant's existing comment", operation_id=uuid4())
        tenant, run = self.start()
        with patch("chatballs.integrations.execution.runner._commit", side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                run_one(tenant, run.public_id)
        with tenant_atomic(tenant):
            self.assertFalse(ConversationComment.objects.filter(organization=self.organization).exists())
            self.assertFalse(NativeEffectReceipt.objects.filter(organization=self.organization).exists())
            step = run.steps.get()
            self.assertIsNone(step.sent_at)
            past = timezone.now() - timedelta(seconds=1)
            run.steps.update(lease_until=past, due_at=past)
        run_one(tenant, run.public_id)
        with tenant_atomic(tenant):
            self.assertEqual(ConversationComment.objects.filter(organization=self.organization).count(), 1)
            self.assertEqual(NativeEffectReceipt.objects.filter(organization=self.organization).count(), 1)
        with tenant_atomic(foreign_tenant):
            self.assertEqual(ConversationComment.objects.get(pk=prior.pk).text, "Another tenant's existing comment")

    def test_receipt_has_forced_runtime_rls_and_cannot_change_tenant(self):
        tenant, run = self.start()
        run_one(tenant, run.public_id)
        with tenant_atomic(tenant):
            receipt = NativeEffectReceipt.objects.get(step__run=run)
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE chatballs_runtime_app")
        try:
            with tenant_atomic(self.foreign.pk):
                self.assertFalse(NativeEffectReceipt.objects.filter(pk=receipt.pk).exists())
            with tenant_atomic(tenant):
                self.assertTrue(NativeEffectReceipt.objects.filter(pk=receipt.pk).exists())
                with self.assertRaises((IntegrityError, ProgrammingError)), transaction.atomic():
                    NativeEffectReceipt.objects.filter(pk=receipt.pk).update(organization_id=self.foreign.pk)
        finally:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE")

    def test_revoked_native_grant_prevents_effect_after_approval(self):
        user = HumanUser.objects.create_user(email="native-member@example.test")
        membership = OrganizationMembership.objects.create(organization=self.organization,
            user=user, role="EMPLOYEE")
        tenant = TenantContext.for_membership(membership)
        with tenant_atomic(self.context):
            self.conversation.assigned_operator = user
            self.conversation.control_mode = "HUMAN"
            self.conversation.save(update_fields=["assigned_operator", "control_mode"])
            grant = ActionGrant.objects.create(organization=self.organization, membership=membership,
                native_key="comments.post", operation_key="", scope="conversation")
        _, run = self.start(actor=tenant)
        with tenant_atomic(tenant):
            grant.enabled = False
            grant.save(update_fields=["enabled"])
        run_one(tenant, run.public_id)
        with tenant_atomic(self.context):
            run.refresh_from_db()
            self.assertEqual(run.state, "failed")
            self.assertEqual(run.steps.get().error_code, "permission")
            self.assertFalse(ConversationComment.objects.filter(organization=self.organization).exists())
