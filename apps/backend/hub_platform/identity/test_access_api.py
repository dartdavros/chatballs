from django.test import TestCase
from hub_platform.testing import TenantAPIClient as APIClient

from hub_platform.events.models import OutboxEvent
from hub_platform.identity.models import (
    AccessProfile,
    AccessProfileCapability,
    Department,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)


class AccessManagementApiTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Example", slug="access-api")
        self.sales = Department.objects.create(
            organization=self.organization, code="sales", name="Sales"
        )
        self.owner = self._employee("owner@access.test", EmployeeRole.OWNER)
        self.admin = self._employee("admin@access.test", EmployeeRole.ADMIN)
        self.employee = self._employee(
            "employee@access.test", EmployeeRole.EMPLOYEE, self.sales
        )
        self.other_admin = self._employee("other-admin@access.test", EmployeeRole.ADMIN)
        self.client = APIClient()
        self.client.force_authenticate(self.owner.user)

    def _employee(
        self, email: str, role: str, department: Department | None = None
    ) -> OrganizationMembership:
        user = HumanUser.objects.create_user(email=email, password="Password-123")
        return OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=role,
            position_title="Specialist",
            primary_department=department,
        )

    def test_profile_and_assignment_crud(self) -> None:
        created = self.client.post(
            "/api/v1/access-profiles/",
            {
                "name": "Sales reader",
                "capabilities": ["customers.view", "conversations.view"],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        profile_id = created.json()["profile"]["id"]
        self.assertEqual(created.json()["profile"]["allowedScopes"], ["DEPARTMENT", "ORGANIZATION"])

        assigned = self.client.post(
            f"/api/v1/employees/{self.employee.user_id}/access-assignments/",
            {
                "profileId": profile_id,
                "scopeType": "DEPARTMENT",
                "departmentId": self.sales.id,
            },
            format="json",
        )
        self.assertEqual(assigned.status_code, 201)
        assignment_id = assigned.json()["assignment"]["id"]

        revoked = self.client.delete(
            f"/api/v1/employees/{self.employee.user_id}/access-assignments/{assignment_id}/"
        )
        self.assertEqual(revoked.status_code, 200)
        self.assertIsNotNone(revoked.json()["assignment"]["revokedAt"])

    def test_registry_exposes_protected_capabilities_as_read_only(self) -> None:
        response = self.client.get("/api/v1/access-profiles/capabilities/")

        self.assertEqual(response.status_code, 200)
        by_code = {item["code"]: item for item in response.json()["items"]}
        self.assertTrue(by_code["ownership.transfer"]["protected"])
        self.assertFalse(by_code["ownership.transfer"]["assignable"])

    def test_department_assignment_rejects_organization_only_profile(self) -> None:
        profile = AccessProfile.objects.create(
            organization=self.organization, name="Company reader"
        )
        AccessProfileCapability.objects.create(
            access_profile=profile, capability_code="company.view"
        )

        response = self.client.post(
            f"/api/v1/employees/{self.employee.user_id}/access-assignments/",
            {
                "profileId": profile.id,
                "scopeType": "DEPARTMENT",
                "departmentId": self.sales.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(profile.assignments.exists())

    def test_profile_update_rejects_capabilities_that_break_active_scope(self) -> None:
        profile = AccessProfile.objects.create(
            organization=self.organization, name="Department reader"
        )
        AccessProfileCapability.objects.create(
            access_profile=profile, capability_code="customers.view"
        )
        assigned = self.client.post(
            f"/api/v1/employees/{self.employee.user_id}/access-assignments/",
            {
                "profileId": profile.id,
                "scopeType": "DEPARTMENT",
                "departmentId": self.sales.id,
            },
            format="json",
        )
        self.assertEqual(assigned.status_code, 201)

        response = self.client.patch(
            f"/api/v1/access-profiles/{profile.id}/",
            {"capabilities": ["company.view"]},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            list(profile.capability_links.values_list("capability_code", flat=True)),
            ["customers.view"],
        )

    def test_system_profile_is_read_only(self) -> None:
        profile = AccessProfile.objects.create(
            organization=self.organization,
            name="System profile",
            is_system=True,
        )

        response = self.client.patch(
            f"/api/v1/access-profiles/{profile.id}/",
            {"isActive": False},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        profile.refresh_from_db()
        self.assertTrue(profile.is_active)

    def test_registry_rejects_unknown_and_protected_codes(self) -> None:
        for code in ("invented.permission", "ownership.transfer"):
            response = self.client.post(
                "/api/v1/access-profiles/",
                {"name": f"Invalid {code}", "capabilities": [code]},
                format="json",
            )
            self.assertEqual(response.status_code, 400)
        self.assertFalse(AccessProfile.objects.filter(name__startswith="Invalid").exists())

    def test_admin_cannot_change_other_admin_access(self) -> None:
        profile = AccessProfile.objects.create(
            organization=self.organization, name="Empty profile"
        )
        self.client.force_authenticate(self.admin.user)
        response = self.client.post(
            f"/api/v1/employees/{self.other_admin.user_id}/access-assignments/",
            {"profileId": profile.id, "scopeType": "ORGANIZATION"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_cannot_assign_profile_to_admin(self) -> None:
        profile = AccessProfile.objects.create(
            organization=self.organization, name="Employee profile"
        )

        response = self.client.post(
            f"/api/v1/employees/{self.admin.user_id}/access-assignments/",
            {"profileId": profile.id, "scopeType": "ORGANIZATION"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(profile.assignments.exists())

    def test_profile_name_is_required(self) -> None:
        response = self.client.post(
            "/api/v1/access-profiles/",
            {"name": "   ", "capabilities": []},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_employee_cannot_manage_profiles(self) -> None:
        self.client.force_authenticate(self.employee.user)
        response = self.client.get("/api/v1/access-profiles/")
        self.assertEqual(response.status_code, 403)

    def test_employee_create_accepts_scoped_assignments_atomically(self) -> None:
        profile = AccessProfile.objects.create(
            organization=self.organization, name="New employee profile"
        )
        response = self.client.post(
            "/api/v1/employees/operators/",
            {
                "email": "new@access.test",
                "fullName": "New Employee",
                "positionTitle": "Specialist",
                "role": "EMPLOYEE",
                "department": "sales",
                "accessAssignments": [
                    {
                        "profileId": profile.id,
                        "scopeType": "DEPARTMENT",
                        "departmentId": self.sales.id,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        created = OrganizationMembership.objects.get(user__email="new@access.test")
        self.assertEqual(created.access_assignments.get().department, self.sales)

    def test_employee_create_without_password_queues_first_access_email(self) -> None:
        response = self.client.post(
            "/api/v1/employees/operators/",
            {
                "email": "invited@access.test",
                "fullName": "Invited Employee",
                "positionTitle": "Specialist",
                "role": "EMPLOYEE",
                "department": "sales",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        created = HumanUser.objects.get(email="invited@access.test")
        self.assertFalse(created.has_usable_password())
        self.assertTrue(created.must_change_password)
        self.assertTrue(
            OutboxEvent.objects.filter(
                aggregate_id=str(created.id),
                event_type="identity.initial_access_requested",
            ).exists()
        )
