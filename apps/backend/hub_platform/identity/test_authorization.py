from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from hub_platform.identity.capabilities import ScopeType
from hub_platform.identity.models import (
    AccessProfile,
    AccessProfileCapability,
    Department,
    EmployeeAccessAssignment,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.identity.policy import (
    ResourceScope,
    accessible_department_ids,
    authorize,
    get_effective_access,
)


class CapabilityPolicyTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Example", slug="example")
        self.other_organization = Organization.objects.create(name="Other", slug="other")
        self.sales = Department.objects.create(
            organization=self.organization, code="sales", name="Sales"
        )
        self.support = Department.objects.create(
            organization=self.organization, code="support", name="Support"
        )
        self.owner = self._employee("owner@example.test", EmployeeRole.OWNER)
        self.admin = self._employee("admin@example.test", EmployeeRole.ADMIN)
        self.employee = self._employee(
            "employee@example.test", EmployeeRole.EMPLOYEE, self.sales
        )

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

    def _profile(self, name: str, *codes: str) -> AccessProfile:
        profile = AccessProfile.objects.create(organization=self.organization, name=name)
        for code in codes:
            AccessProfileCapability.objects.create(
                access_profile=profile, capability_code=code
            )
        return profile

    def _assign(
        self,
        profile: AccessProfile,
        *,
        department: Department | None = None,
    ) -> EmployeeAccessAssignment:
        return EmployeeAccessAssignment.objects.create(
            employee=self.employee,
            access_profile=profile,
            scope_type=ScopeType.DEPARTMENT if department else ScopeType.ORGANIZATION,
            department=department,
            assigned_by=self.owner,
        )

    def test_owner_and_admin_role_policy(self) -> None:
        organization_scope = ResourceScope(self.organization.id)
        self.assertTrue(authorize(self.owner, "ownership.transfer", organization_scope))
        self.assertFalse(authorize(self.admin, "ownership.transfer", organization_scope))
        self.assertTrue(authorize(self.admin, "integrations.manage", organization_scope))

    def test_department_assignment_does_not_cross_department(self) -> None:
        self._assign(
            self._profile("Sales operator", "conversations.view"), department=self.sales
        )
        self.assertTrue(
            authorize(
                self.employee,
                "conversations.view",
                ResourceScope(self.organization.id, self.sales.id),
            )
        )
        self.assertFalse(
            authorize(
                self.employee,
                "conversations.view",
                ResourceScope(self.organization.id, self.support.id),
            )
        )
        self.assertFalse(
            authorize(
                self.employee,
                "conversations.view",
                ResourceScope(self.other_organization.id, self.sales.id),
            )
        )

    def test_primary_department_never_grants_access(self) -> None:
        self.assertFalse(
            authorize(
                self.employee,
                "conversations.view",
                ResourceScope(self.organization.id, self.sales.id),
            )
        )

    def test_organization_assignment_covers_departments(self) -> None:
        self._assign(self._profile("Company reader", "conversations.view"))
        self.assertTrue(
            authorize(
                self.employee,
                "conversations.view",
                ResourceScope(self.organization.id, self.support.id),
            )
        )
        self.assertIsNone(accessible_department_ids(self.employee, "conversations.view"))

    def test_multiple_assignments_are_unioned_and_exposed(self) -> None:
        self._assign(
            self._profile("Sales reader", "customers.view", "conversations.view"),
            department=self.sales,
        )
        self._assign(
            self._profile("Support reader", "support.view", "conversations.view"),
            department=self.support,
        )
        access = get_effective_access(self.employee)
        self.assertEqual(
            access["capabilities"],
            ["conversations.view", "customers.view", "support.view"],
        )
        self.assertEqual(
            accessible_department_ids(self.employee, "conversations.view"),
            {self.sales.id, self.support.id},
        )
        self.assertEqual(len(access["accessScopes"]), 2)

    def test_revoked_or_disabled_assignment_stops_access_immediately(self) -> None:
        profile = self._profile("Reader", "products.view")
        assignment = self._assign(profile, department=self.sales)
        scope = ResourceScope(self.organization.id, self.sales.id)
        self.assertTrue(authorize(self.employee, "products.view", scope))
        assignment.revoked_at = timezone.now()
        assignment.save(update_fields=["revoked_at"])
        self.assertFalse(authorize(self.employee, "products.view", scope))

        second = self._assign(profile, department=self.sales)
        profile.is_active = False
        profile.save()
        self.assertFalse(authorize(self.employee, "products.view", scope))
        self.assertIsNotNone(second.id)

    def test_unknown_and_protected_capabilities_are_rejected(self) -> None:
        profile = AccessProfile.objects.create(organization=self.organization, name="Invalid")
        with self.assertRaises(ValidationError):
            AccessProfileCapability.objects.create(
                access_profile=profile, capability_code="invented.permission"
            )
        with self.assertRaises(ValidationError):
            AccessProfileCapability.objects.create(
                access_profile=profile, capability_code="ownership.transfer"
            )

    def test_assignment_organization_and_scope_invariants(self) -> None:
        profile = self._profile("Reader", "products.view")
        with self.assertRaises(ValidationError):
            EmployeeAccessAssignment.objects.create(
                employee=self.employee,
                access_profile=profile,
                scope_type=ScopeType.DEPARTMENT,
                department=None,
                assigned_by=self.owner,
            )
