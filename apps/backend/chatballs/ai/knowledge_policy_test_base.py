from django.test import TestCase

from chatballs.ai.knowledge_categories import (
    create_category,
    ensure_uncategorized_category,
)
from chatballs.ai.models import Knowledge
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.tenancy.context import TenantContext


class KnowledgePolicyTestBase(TestCase):
    """База knowledge-тестов: библиотека общая для организации (ADR-CHATBALLS-0041 §8),
    доступ ролевой — у EMPLOYEE нет ai.*, у OWNER/ADMIN есть всё."""

    def setUp(self) -> None:
        self.organization = Organization.objects.create(
            name="Example", slug="knowledge-policy"
        )
        self.other_organization = Organization.objects.create(
            name="Other", slug="knowledge-policy-other"
        )
        ensure_uncategorized_category(self.organization)
        self.other_category = ensure_uncategorized_category(self.other_organization)
        self.system_context = TenantContext.for_resource(self.organization)
        self.owner = self._membership("owner@policy.test", EmployeeRole.OWNER)
        self.admin = self._membership("admin@policy.test", EmployeeRole.ADMIN)
        self.employee = self._membership("employee@policy.test", EmployeeRole.EMPLOYEE)
        self.owner_context = TenantContext.for_membership(self.owner)
        self.admin_context = TenantContext.for_membership(self.admin)
        self.employee_context = TenantContext.for_membership(self.employee)

        self.products = create_category(
            context=self.system_context, name="Products", sort_order=10
        )
        self.shared = self._knowledge("Shared handbook", "Common company rules")
        self.sales_only = self._knowledge("Sales playbook", "Pricing and qualification")
        self.support_only = self._knowledge("Support runbook", "Incidents and escalation")
        self.disabled = self._knowledge("Legacy script", "Retired", is_enabled=False)

    def _membership(self, email: str, role: str) -> OrganizationMembership:
        user = HumanUser.objects.create_user(email=email, password="Password-123")
        return OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=role,
            position_title="Specialist",
        )

    def _knowledge(
        self, title: str, description: str, *, is_enabled: bool = True
    ) -> Knowledge:
        return Knowledge.objects.create(
            organization=self.organization,
            category=self.products,
            title=title,
            description=description,
            is_enabled=is_enabled,
        )
