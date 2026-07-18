from hub_platform.ai.knowledge_policy import (
    employee_can_create_knowledge,
    employee_can_manage_categories,
    employee_can_read_knowledge,
    employee_can_write_knowledge,
)
from hub_platform.ai.knowledge_policy_test_base import KnowledgePolicyTestBase
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.models import Knowledge
from hub_platform.ai.selectors import (
    knowledge_for_employee,
    writable_knowledge_for_employee,
)


class KnowledgePolicyTests(KnowledgePolicyTestBase):
    def test_read_policy_is_tenant_safe_and_department_scoped(self) -> None:
        visible_ids = set(
            knowledge_for_employee(context=self.sales_context).values_list(
                "id", flat=True
            )
        )
        self.assertEqual(
            visible_ids,
            {
                self.shared.id,
                self.sales_only.id,
                self.multi_department.id,
                self.disabled_sales.id,
            },
        )
        self.assertFalse(
            employee_can_read_knowledge(
                context=self.sales_context, knowledge=self.support_only
            )
        )
        other_knowledge = Knowledge.objects.create(
            organization=self.other_organization,
            category=self.other_category,
            title="Other tenant",
        )
        self.assertFalse(
            employee_can_read_knowledge(
                context=self.owner_context, knowledge=other_knowledge
            )
        )

    def test_write_policy_requires_full_current_and_new_department_coverage(self) -> None:
        sales_writable_ids = set(
            writable_knowledge_for_employee(
                context=self.sales_context
            ).values_list("id", flat=True)
        )
        self.assertEqual(sales_writable_ids, {self.sales_only.id, self.disabled_sales.id})
        self.assertFalse(
            employee_can_write_knowledge(
                context=self.sales_context, knowledge=self.shared
            )
        )
        self.assertFalse(
            employee_can_write_knowledge(
                context=self.sales_context, knowledge=self.multi_department
            )
        )
        self.assertFalse(
            employee_can_write_knowledge(
                context=self.sales_context,
                knowledge=self.sales_only,
                visibility=KnowledgeVisibility.DEPARTMENTS,
                department_ids=[self.sales.id, self.support.id],
            )
        )
        self.assertTrue(
            employee_can_write_knowledge(
                context=self.all_departments_context,
                knowledge=self.multi_department,
            )
        )
        self.assertTrue(
            employee_can_write_knowledge(
                context=self.organization_manager_context, knowledge=self.shared
            )
        )

    def test_create_and_category_policy_distinguish_department_and_org_scope(self) -> None:
        self.assertTrue(
            employee_can_create_knowledge(
                context=self.sales_context,
                visibility=KnowledgeVisibility.DEPARTMENTS,
                department_ids=[self.sales.id],
            )
        )
        self.assertFalse(
            employee_can_create_knowledge(
                context=self.sales_context,
                visibility=KnowledgeVisibility.ORGANIZATION,
                department_ids=[],
            )
        )
        self.assertFalse(employee_can_manage_categories(context=self.sales_context))
        self.assertTrue(
            employee_can_manage_categories(context=self.organization_manager_context)
        )
