"""Group effects retain tenant boundaries, role checks and supervision audit."""

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity import group_services
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.models import AuditEvent, HumanUser, OrganizationMembership
from chatballs.identity.supervision_models import EmployeeGroupSupervision
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.runner import run_one
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeGroupTests(CommentTransactionTestBase):
    def test_create_update_delete_and_replay_keep_product_audit(self):
        run, output = execute_action(self.context, "groups.post", {
            "name": "Support", "color": "#ABCDEF", "memberIds": [self.author.id]})
        self.assertEqual(run.state, "completed")
        group_id = output["group"]["id"]
        self.assertEqual(output["group"]["color"], "#abcdef")
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(EmployeeGroup.objects.filter(organization=self.organization).count(), 1)
            self.assertEqual(AuditEvent.objects.filter(action="identity.group_created").count(), 1)
        run, output = execute_action(self.context, "groups.group.patch", {
            "group_id": group_id, "name": "Operations", "memberIds": []})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["group"]["memberCount"], 0)
        run, output = execute_action(self.context, "groups.get", {})
        self.assertEqual(run.state, "completed")
        self.assertEqual([row["name"] for row in output["items"]], ["Operations"])
        run, output = execute_action(self.context, "groups.group.delete", {"group_id": group_id})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output, {"deleted": True})

    def test_foreign_member_rejection_rolls_back_name_and_members(self):
        with tenant_atomic(self.context):
            group = EmployeeGroup.objects.create(organization=self.organization, name="Original")
        run, _ = execute_action(self.context, "groups.group.patch", {
            "group_id": group.id, "name": "Changed", "memberIds": [self.foreign_author.id]})
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            group.refresh_from_db()
            self.assertEqual(group.name, "Original")
            self.assertFalse(AuditEvent.objects.filter(action="identity.group_updated").exists())

    def test_foreign_group_is_not_addressable(self):
        with tenant_atomic(TenantContext.for_resource(self.foreign)):
            group = EmployeeGroup.objects.create(organization=self.foreign, name="Foreign")
        for key in ("groups.group.patch", "groups.group.delete"):
            run, _ = execute_action(self.context, key, {"group_id": group.id})
            self.assertEqual(run.state, "failed")

    def test_service_checks_current_role_and_blocked_membership(self):
        for role in ("EMPLOYEE", "SUPERVISOR"):
            user = HumanUser.objects.create_user(email=f"{role}@native-groups.test")
            member = OrganizationMembership.objects.create(
                organization=self.organization, user=user, role=role)
            context = TenantContext.for_membership(member)
            with tenant_atomic(context), self.assertRaises(PermissionDenied):
                group_services.create_group(context, {"name": "Forbidden"})
        OrganizationMembership.objects.filter(pk=self.membership.pk).update(blocked_at=timezone.now())
        with tenant_atomic(self.context), self.assertRaises(PermissionDenied):
            group_services.create_group(self.context, {"name": "Blocked"})

    def test_delete_removes_supervision_without_changing_role_and_audits_actor(self):
        user = HumanUser.objects.create_user(email="supervisor@native-groups.test")
        supervisor = OrganizationMembership.objects.create(
            organization=self.organization, user=user, role="SUPERVISOR")
        with tenant_atomic(self.context):
            group = EmployeeGroup.objects.create(organization=self.organization, name="Control")
            EmployeeGroupSupervision.objects.create(
                organization=self.organization, group=group, employee=supervisor)
        run, _ = execute_action(self.context, "groups.group.delete", {"group_id": group.id})
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.context):
            supervisor.refresh_from_db()
            self.assertEqual(supervisor.role, "SUPERVISOR")
            self.assertFalse(supervisor.supervision_links.exists())
            event = AuditEvent.objects.get(action="identity.employee_supervised_groups_changed")
            self.assertEqual(event.actor_id, self.author.id)
            self.assertEqual(event.payload["oldGroupIds"], [group.id])
            self.assertEqual(event.payload["groupIds"], [])
