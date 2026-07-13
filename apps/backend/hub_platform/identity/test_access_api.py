from django.test import TestCase
from rest_framework.test import APIClient

from hub_platform.identity.models import (
    AccessProfile,
    Department,
    EmployeeProfile,
    EmployeeRole,
    HumanUser,
    Organization,
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
    ) -> EmployeeProfile:
        user = HumanUser.objects.create_user(email=email, password="Password-123")
        return EmployeeProfile.objects.create(
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
                "capabilities": ["sales.view", "conversations.view"],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        profile_id = created.json()["profile"]["id"]

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
                "temporaryPassword": "Temporary-123",
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
        created = EmployeeProfile.objects.get(user__email="new@access.test")
        self.assertEqual(created.access_assignments.get().department, self.sales)
