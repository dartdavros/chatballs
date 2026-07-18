from django.test import TestCase

from hub_platform.ai.knowledge_categories import (
    create_category,
    ensure_uncategorized_category,
)
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.knowledge_visibility import replace_knowledge_visibility
from hub_platform.ai.models import Knowledge
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
from hub_platform.tenancy.context import TenantContext


class KnowledgePolicyTestBase(TestCase):
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
        self.sales = Department.objects.create(
            organization=self.organization, code="sales", name="Sales"
        )
        self.support = Department.objects.create(
            organization=self.organization, code="support", name="Support"
        )
        self.owner = self._membership("owner@policy.test", EmployeeRole.OWNER)
        self.sales_employee = self._membership(
            "sales@policy.test", EmployeeRole.EMPLOYEE
        )
        self.all_departments_employee = self._membership(
            "all@policy.test", EmployeeRole.EMPLOYEE
        )
        self.organization_manager = self._membership(
            "manager@policy.test", EmployeeRole.EMPLOYEE
        )
        self._assign(
            self.sales_employee,
            "Sales AI",
            ("ai.view", "ai.manage"),
            self.sales,
        )
        self._assign(
            self.all_departments_employee,
            "Sales AI",
            ("ai.view", "ai.manage"),
            self.sales,
        )
        self._assign(
            self.all_departments_employee,
            "Support AI",
            ("ai.view", "ai.manage"),
            self.support,
        )
        self._assign(
            self.organization_manager,
            "Organization AI",
            ("ai.view", "ai.manage"),
            None,
        )
        self.sales_context = TenantContext.for_membership(self.sales_employee)
        self.all_departments_context = TenantContext.for_membership(
            self.all_departments_employee
        )
        self.organization_manager_context = TenantContext.for_membership(
            self.organization_manager
        )
        self.owner_context = TenantContext.for_membership(self.owner)

        self.products = create_category(
            context=self.system_context, name="Products", sort_order=10
        )
        self.shared = self._knowledge(
            "Shared handbook", "Common company rules"
        )
        self.sales_only = self._knowledge(
            "Sales playbook", "Pricing and qualification"
        )
        self.support_only = self._knowledge(
            "Support runbook", "Incidents and escalation"
        )
        self.multi_department = self._knowledge(
            "Customer lifecycle", "Sales to support handoff"
        )
        self.disabled_sales = self._knowledge(
            "Legacy sales", "Retired script", is_enabled=False
        )
        self._scope(self.sales_only, self.sales)
        self._scope(self.support_only, self.support)
        self._scope(self.multi_department, self.sales, self.support)
        self._scope(self.disabled_sales, self.sales)

    def _membership(self, email: str, role: str) -> OrganizationMembership:
        user = HumanUser.objects.create_user(email=email, password="Password-123")
        return OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=role,
            position_title="Specialist",
        )

    def _assign(
        self,
        employee: OrganizationMembership,
        name: str,
        capabilities: tuple[str, ...],
        department: Department | None,
    ) -> None:
        profile = AccessProfile.objects.create(
            organization=self.organization,
            name=f"{name} {employee.id}",
        )
        for capability in capabilities:
            AccessProfileCapability.objects.create(
                access_profile=profile, capability_code=capability
            )
        EmployeeAccessAssignment.objects.create(
            employee=employee,
            access_profile=profile,
            scope_type=(
                ScopeType.DEPARTMENT if department else ScopeType.ORGANIZATION
            ),
            department=department,
            assigned_by=self.owner,
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

    def _scope(self, knowledge: Knowledge, *departments: Department) -> None:
        replace_knowledge_visibility(
            context=self.system_context,
            knowledge=knowledge,
            visibility=KnowledgeVisibility.DEPARTMENTS,
            department_ids=[department.id for department in departments],
        )
        knowledge.refresh_from_db()
