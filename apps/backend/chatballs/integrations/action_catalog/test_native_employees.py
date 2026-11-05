"""Native employee effects retain governance, tenant checks, audit and credential delivery."""

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.events.models import OutboxEvent
from chatballs.identity.event_handlers import INITIAL_ACCESS_REQUESTED
from chatballs.identity.invitation_models import OrganizationInvitation
from chatballs.identity.invitation_service import MEMBERSHIP_INVITATION_REQUESTED
from chatballs.identity.models import AuditEvent, HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.native_results import restored
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeEmployeeTests(CommentTransactionTestBase):
    def test_create_update_and_reset_use_mail_without_password_output_or_replay(self):
        run, output = execute_action(self.context, "employees.post", {
            "email": "new@employee.test", "fullName": "New employee", "positionTitle": "Support"})
        self.assertEqual(run.state, "completed")
        self.assertNotIn("password", output)
        user_id = output["employee"]["id"]
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(OutboxEvent.objects.filter(event_type=INITIAL_ACCESS_REQUESTED).count(), 1)
            self.assertEqual(HumanUser.objects.filter(email="new@employee.test").count(), 1)
            self.assertFalse(HumanUser.objects.get(pk=user_id).has_usable_password())
            self.assertNotIn("password", NativeEffectReceipt.objects.get(step__run=run).definition["result"])
        run, output = execute_action(self.context, "employees.update", {
            "user_id": user_id, "email": "new@employee.test", "fullName": "Updated", "role": "SUPERVISOR"})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["employee"]["role"], "SUPERVISOR")
        run, output = execute_action(self.context, "employees.reset_password", {"user_id": user_id})
        self.assertEqual(run.state, "completed")
        self.assertNotIn("password", output)
        run, output = execute_action(self.context, "employees.get", {"q": "Updated"})
        self.assertEqual(run.state, "completed")
        self.assertEqual([row["id"] for row in output["items"]], [user_id])
        run, output = execute_action(self.context, "employees.detail.get", {"user_id": user_id})
        self.assertEqual(run.state, "completed")
        self.assertTrue(output["employee"]["auditEvents"])

    def test_owner_block_denial_is_durable_and_foreign_employee_is_unreachable(self):
        run, output = execute_action(self.context, "employees.block", {"user_id": self.author.pk})
        self.assertEqual(run.state, "failed")
        self.assertFalse(output)
        with tenant_atomic(self.context):
            receipt = NativeEffectReceipt.objects.get(step__run=run)
            self.assertEqual(restored(receipt).state, "failed")
            self.assertEqual(restored(receipt).error_code, "permission")
            self.assertEqual(AuditEvent.objects.filter(action="identity.employee_privileged_action_denied").count(), 1)
            self.membership.refresh_from_db()
            self.assertFalse(self.membership.is_blocked)
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(AuditEvent.objects.filter(action="identity.employee_privileged_action_denied").count(), 1)
        run, _ = execute_action(self.context, "employees.block", {"user_id": self.foreign_author.pk})
        self.assertEqual(run.state, "failed")

    def test_invitation_lifecycle_uses_existing_user_and_single_outbox_per_run(self):
        run, output = execute_action(self.context, "employees.post", {
            "email": self.foreign_author.email, "fullName": "Existing", "positionTitle": "Support"})
        self.assertEqual(run.state, "completed")
        self.assertTrue(output["invited"])
        self.assertIsNone(output["employee"])
        with tenant_atomic(self.context):
            invitation = OrganizationInvitation.objects.get(organization=self.organization)
            self.assertFalse(OrganizationMembership.objects.filter(organization=self.organization, user=self.foreign_author).exists())
        run, output = execute_action(self.context, "employees.invitation.resend", {"invitation_id": invitation.pk})
        self.assertEqual(run.state, "completed")
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(OutboxEvent.objects.filter(event_type=MEMBERSHIP_INVITATION_REQUESTED).count(), 2)
        run, _ = execute_action(self.context, "employees.invitation.revoke", {"invitation_id": invitation.pk})
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.context):
            invitation.refresh_from_db()
            self.assertIsNotNone(invitation.revoked_at)

    def test_multi_org_password_and_admin_ownership_transfer_remain_forbidden(self):
        with tenant_atomic(self.context):
            member = OrganizationMembership.objects.create(
                organization=self.organization, user=self.foreign_author, role="ADMIN", position_title="Admin")
        run, _ = execute_action(self.context, "employees.reset_password", {"user_id": self.foreign_author.pk})
        self.assertEqual(run.state, "failed")
        run, _ = execute_action(TenantContext.for_membership(member), "employees.transfer_ownership", {"user_id": self.author.pk})
        self.assertEqual(run.state, "failed")
        run, output = execute_action(self.context, "employees.transfer_ownership", {"user_id": self.foreign_author.pk})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["employee"]["role"], "OWNER")
        self.assertEqual(output["previousOwner"]["role"], "ADMIN")
