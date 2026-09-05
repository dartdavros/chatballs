from django.test import TestCase

from chatballs.identity.group_models import EmployeeGroup, EmployeeGroupMember
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.identity.policy import (
    ResourceScope,
    authorize,
    conversation_visibility,
    get_effective_access,
    has_capability_any_scope,
)


class RolePolicyTests(TestCase):
    """Ролевая авторизация SPEC-HUB-0031 §3 + видимость по группам ADR-HUB-0043."""

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Example", slug="example")
        self.other_organization = Organization.objects.create(name="Other", slug="other")
        self.operators = EmployeeGroup.objects.create(
            organization=self.organization, name="Операторы"
        )
        self.support = EmployeeGroup.objects.create(
            organization=self.organization, name="Поддержка"
        )
        self.owner = self._employee("owner@example.test", EmployeeRole.OWNER)
        self.admin = self._employee("admin@example.test", EmployeeRole.ADMIN)
        self.employee = self._employee("employee@example.test", EmployeeRole.EMPLOYEE)
        EmployeeGroupMember.objects.create(
            organization=self.organization, group=self.operators, employee=self.employee
        )

    def _employee(self, email: str, role: str) -> OrganizationMembership:
        user = HumanUser.objects.create_user(email=email, password="Password-123")
        return OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=role,
            position_title="Specialist",
        )

    def test_owner_and_admin_are_identical_except_ownership_transfer(self) -> None:
        scope = ResourceScope(self.organization.id)
        for capability in (
            "employees.manage",
            "employees.manage_privileged",
            "integrations.manage",
            "channels.manage",
            "ai.manage",
            "settings.manage",
            "groups.manage",
        ):
            self.assertTrue(authorize(self.owner, capability, scope), capability)
            self.assertTrue(authorize(self.admin, capability, scope), capability)
        self.assertTrue(authorize(self.owner, "ownership.transfer", scope))
        self.assertFalse(authorize(self.admin, "ownership.transfer", scope))

    def test_employee_is_limited_to_chat_capabilities(self) -> None:
        scope = ResourceScope(self.organization.id)
        self.assertTrue(authorize(self.employee, "conversations.view", scope))
        self.assertTrue(authorize(self.employee, "conversations.operate", scope))
        self.assertTrue(authorize(self.employee, "customers.view", scope))
        self.assertFalse(authorize(self.employee, "employees.view", scope))
        self.assertFalse(authorize(self.employee, "ai.view", scope))
        self.assertFalse(authorize(self.employee, "channels.view", scope))
        self.assertFalse(authorize(self.employee, "settings.manage", scope))

    def test_cross_organization_scope_is_denied(self) -> None:
        self.assertFalse(
            authorize(
                self.owner,
                "conversations.view",
                ResourceScope(self.other_organization.id),
            )
        )

    def test_blocked_member_loses_access(self) -> None:
        self.employee.block()
        self.assertFalse(
            has_capability_any_scope(self.employee, "conversations.view")
        )

    def test_conversation_visibility_scopes(self) -> None:
        self.assertIsNone(conversation_visibility(self.owner))
        self.assertIsNone(conversation_visibility(self.admin))
        scope = conversation_visibility(self.employee)
        self.assertEqual(scope["group_ids"], {self.operators.id})
        self.assertEqual(scope["user_id"], self.employee.user_id)

    def test_effective_access_payload(self) -> None:
        owner_access = get_effective_access(self.owner)
        self.assertIn("ownership.transfer", owner_access["capabilities"])
        admin_access = get_effective_access(self.admin)
        self.assertNotIn("ownership.transfer", admin_access["capabilities"])
        self.assertIn("employees.manage_privileged", admin_access["capabilities"])
        employee_access = get_effective_access(self.employee)
        self.assertEqual(
            employee_access["groups"],
            [{"id": self.operators.id, "name": "Операторы"}],
        )
        self.assertIn("conversations.view", employee_access["capabilities"])
        self.assertNotIn("ai.view", employee_access["capabilities"])
