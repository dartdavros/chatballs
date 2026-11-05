"""Availability actions preserve versions and the exact supervision boundary."""

from uuid import uuid4

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.group_models import EmployeeGroup, EmployeeGroupMember
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.identity.supervision_models import EmployeeGroupSupervision
from chatballs.identity.work_status_models import WorkStatusOperation
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeAvailabilityTests(CommentTransactionTestBase):
    def test_status_change_replays_original_operation_and_rejects_stale_version(self):
        args = {"status": "READY", "expectedVersion": 0, "operationId": str(uuid4())}
        run, output = execute_action(self.context, "availability.own.post", args)
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["version"], 1)
        run, replay = execute_action(self.context, "availability.own.post", args)
        self.assertEqual(run.state, "completed")
        self.assertEqual(output, replay)
        run, _ = execute_action(self.context, "availability.own.post", {
            "status": "BUSY", "expectedVersion": 0, "operationId": str(uuid4())})
        self.assertEqual(run.state, "failed")
        run, history = execute_action(self.context, "availability.own.history.get", {})
        self.assertEqual(run.state, "completed")
        self.assertEqual(history["total"], 1)
        with tenant_atomic(self.context):
            self.assertEqual(WorkStatusOperation.objects.filter(membership=self.membership).count(), 1)

    def test_employee_read_keeps_supervision_and_immediate_revocation(self):
        user = HumanUser.objects.create_user(email="supervisor@native-availability.test")
        supervisor = OrganizationMembership.objects.create(
            organization=self.organization, user=user, role="SUPERVISOR")
        context = TenantContext.for_membership(supervisor)
        with tenant_atomic(context):
            group = EmployeeGroup.objects.create(organization=self.organization, name="Controlled")
            EmployeeGroupMember.objects.create(organization=self.organization, group=group, employee=self.membership)
            link = EmployeeGroupSupervision.objects.create(organization=self.organization, group=group, employee=supervisor)
            ActionGrant.objects.create(organization=self.organization, membership=supervisor,
                native_key="availability.employee.get", scope="organization", enabled=True)
        run, _ = execute_action(context, "availability.employee.get", {"user_id": self.author.id})
        self.assertEqual(run.state, "completed")
        with tenant_atomic(context):
            link.delete()
        run, _ = execute_action(context, "availability.employee.get", {"user_id": self.author.id})
        self.assertEqual(run.state, "failed")

    def test_other_organization_is_not_visible_to_owner(self):
        for key in ("availability.employee.get", "availability.employee.history.get"):
            run, _ = execute_action(self.context, key, {"user_id": self.foreign_author.id})
            self.assertEqual(run.state, "failed")
