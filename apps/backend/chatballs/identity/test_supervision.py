from django.test import TestCase

from chatballs.identity.capabilities import EMPLOYEE_CAPABILITIES
from chatballs.identity.governance import EmployeeAction, can_manage_employee
from chatballs.identity.group_models import EmployeeGroup, EmployeeGroupMember
from chatballs.identity.models import (
    AuditEvent,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.identity.policy import conversation_visibility, get_effective_access
from chatballs.identity.supervision_models import EmployeeGroupSupervision
from chatballs.testing import TenantAPIClient


class SupervisionTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Supervision", slug="supervision")
        self.other = Organization.objects.create(name="Other", slug="supervision-other")
        self.owner = self.member("owner", EmployeeRole.OWNER)
        self.admin = self.member("admin", EmployeeRole.ADMIN)
        self.employee = self.member("employee", EmployeeRole.EMPLOYEE)
        self.supervisor = self.member("supervisor", EmployeeRole.SUPERVISOR)
        self.work = EmployeeGroup.objects.create(organization=self.org, name="Work")
        self.control = EmployeeGroup.objects.create(organization=self.org, name="Control")
        self.foreign = EmployeeGroup.objects.create(organization=self.other, name="Foreign")
        EmployeeGroupMember.objects.create(group=self.work, employee=self.employee)
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.owner.user)

    def member(self, name, role):
        user = HumanUser.objects.create_user(email=f"{name}@supervision.test", full_name=name)
        return OrganizationMembership.objects.create(
            user=user, organization=self.org, role=role, position_title="Specialist"
        )

    def update(self, target=None, **changes):
        target = target or self.employee
        body = {"fullName": target.user.full_name, "email": target.user.email}
        body.update(changes)
        return self.client.post(
            f"/api/v1/organizations/{self.org.public_id}/employees/{target.user_id}/update/",
            body, format="json",
        )

    def assign(self):
        response = self.update(role="SUPERVISOR", supervisedGroupIds=[self.control.id])
        self.assertEqual(response.status_code, 200, response.content)
        self.employee.refresh_from_db()
        return response

    def test_owner_and_admin_assign_role_and_separate_scope(self):
        for manager in (self.owner, self.admin):
            with self.subTest(role=manager.role):
                self.client.force_authenticate(manager.user)
                response = self.assign()
                payload = response.json()["employee"]
                self.assertEqual(payload["role"], "SUPERVISOR")
                self.assertEqual(payload["groups"], [{"id": self.work.id, "name": "Work"}])
                self.assertEqual(payload["supervisedGroups"], [
                    {"id": self.control.id, "name": "Control"}
                ])
                self.assertTrue(payload["permissions"]["canChangeSupervisedGroups"])
                self.assertEqual(conversation_visibility(self.employee)["group_ids"], {self.work.id})
                access = get_effective_access(self.employee)
                self.assertEqual(set(access["capabilities"]), EMPLOYEE_CAPABILITIES)
                self.assertEqual(access["supervisedGroups"], payload["supervisedGroups"])

    def test_scope_updates_preserve_omitted_groups_and_clear_on_demotion(self):
        self.assign()
        self.assertEqual(self.update(phone="123").status_code, 200)
        self.assertEqual(self.employee.supervision_links.count(), 1)
        response = self.update(supervisedGroupIds=[])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["employee"]["supervisedGroups"], [])
        self.assertEqual(get_effective_access(self.employee)["supervisedGroups"], [])
        self.assign()
        response = self.update(role="EMPLOYEE")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.employee.supervision_links.exists())
        self.assertEqual(self.employee.group_links.get().group_id, self.work.id)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.role, EmployeeRole.EMPLOYEE)

    def test_invalid_or_foreign_scope_is_atomic(self):
        for ids in ([self.foreign.id], [999999], [True], ["1"], None, "all"):
            with self.subTest(ids=ids):
                response = self.update(role="SUPERVISOR", supervisedGroupIds=ids)
                self.assertEqual(response.status_code, 400)
                self.employee.refresh_from_db()
                self.assertEqual(self.employee.role, EmployeeRole.EMPLOYEE)
                self.assertFalse(self.employee.supervision_links.exists())
                self.assertFalse(AuditEvent.objects.filter(result="SUCCESS").exists())
        self.assertEqual(self.update(supervisedGroupIds=[self.control.id]).status_code, 400)

    def test_duplicates_are_collapsed_and_unchanged_scope_is_not_audited(self):
        response = self.update(role="SUPERVISOR", supervisedGroupIds=[self.control.id] * 2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.employee.supervision_links.count(), 1)
        self.assertEqual(self.update(supervisedGroupIds=[self.control.id]).status_code, 200)
        self.assertEqual(AuditEvent.objects.filter(
            action="identity.employee_supervised_groups_changed"
        ).count(), 1)

    def test_supervisor_and_employee_cannot_manage_self_or_colleagues(self):
        for actor in (self.supervisor, self.employee):
            self.client.force_authenticate(actor.user)
            for target in (actor, self.admin):
                response = self.update(target, role="ADMIN", supervisedGroupIds=[])
                self.assertEqual(response.status_code, 403)
                for action in (
                    EmployeeAction.CHANGE_ROLE, EmployeeAction.CHANGE_SUPERVISED_GROUPS,
                    EmployeeAction.CHANGE_GROUPS, EmployeeAction.RESET_PASSWORD,
                    EmployeeAction.TERMINATE_SESSIONS,
                ):
                    self.assertFalse(can_manage_employee(actor, target, action))
            self.assertEqual(self.client.get(
                f"/api/v1/organizations/{self.org.public_id}/employees/"
            ).status_code, 403)

    def test_foreign_employee_and_owner_role_are_protected(self):
        foreign_user = HumanUser.objects.create_user(email="foreign@supervision.test")
        foreign = OrganizationMembership.objects.create(
            organization=self.other, user=foreign_user, role="EMPLOYEE"
        )
        self.assertEqual(self.update(foreign, role="SUPERVISOR").status_code, 404)
        self.assertEqual(self.update(self.owner, role="SUPERVISOR").status_code, 403)
        self.assertEqual(self.update(role="OWNER").status_code, 400)

    def test_audit_contains_actor_time_and_exact_changes_without_secrets(self):
        self.assign()
        events = AuditEvent.objects.filter(action__in=[
            "identity.employee_role_changed", "identity.employee_supervised_groups_changed"
        ])
        self.assertEqual(events.count(), 2)
        payloads = {event.action: event.payload for event in events}
        self.assertEqual(payloads["identity.employee_role_changed"], {
            "oldRole": "EMPLOYEE", "role": "SUPERVISOR"
        })
        self.assertEqual(payloads["identity.employee_supervised_groups_changed"], {
            "oldGroupIds": [], "groupIds": [self.control.id]
        })
        for event in events:
            self.assertEqual(event.actor_id, self.owner.user_id)
            self.assertEqual(event.organization_id, self.org.id)
            self.assertIsNotNone(event.created_at)
        self.update(role="EMPLOYEE")
        event = AuditEvent.objects.filter(action="identity.employee_supervised_groups_changed").first()
        self.assertEqual(event.payload, {"oldGroupIds": [self.control.id], "groupIds": []})

    def test_detail_and_list_expose_scope_and_existing_roles_stay_unchanged(self):
        self.assign()
        prefix = f"/api/v1/organizations/{self.org.public_id}/employees/"
        detail = self.client.get(f"{prefix}{self.employee.user_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["employee"]["supervisedGroups"][0]["id"], self.control.id)
        listing = self.client.get(prefix, {"role": "SUPERVISOR"})
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.json()["items"]), 2)
        for manager in (self.owner, self.admin):
            manager.refresh_from_db()
        self.assertEqual(self.owner.role, "OWNER")
        self.assertEqual(self.admin.role, "ADMIN")
        self.assertFalse(self.owner.supervision_links.exists())
        self.assertFalse(self.admin.supervision_links.exists())

    def test_scope_never_grants_global_admin_access_and_blocking_removes_effective_area(self):
        EmployeeGroupSupervision.objects.create(employee=self.supervisor, group=self.control)
        access = get_effective_access(self.supervisor)
        self.assertEqual(set(access["capabilities"]), EMPLOYEE_CAPABILITIES)
        self.assertEqual(conversation_visibility(self.supervisor)["group_ids"], set())
        self.supervisor.block()
        self.assertEqual(get_effective_access(self.supervisor), {
            "capabilities": [], "groups": [], "supervisedGroups": [], "reportCapabilities": []
        })

    def test_deleting_control_group_revokes_and_audits_control_area(self):
        self.assign()
        response = self.client.delete(
            f"/api/v1/organizations/{self.org.public_id}/company/groups/{self.control.id}/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.employee.supervision_links.exists())
        event = AuditEvent.objects.filter(action="identity.employee_supervised_groups_changed").first()
        self.assertEqual(event.payload, {"oldGroupIds": [self.control.id], "groupIds": []})
        self.assertEqual(self.employee.group_links.get().group_id, self.work.id)

    def test_transfer_of_ownership_clears_previous_supervision(self):
        self.assign()
        response = self.client.post(
            f"/api/v1/organizations/{self.org.public_id}/employees/{self.employee.user_id}/transfer-ownership/",
            {}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.role, "OWNER")
        self.assertFalse(self.employee.supervision_links.exists())
