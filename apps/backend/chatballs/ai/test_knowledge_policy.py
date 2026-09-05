from django.core.exceptions import PermissionDenied

from chatballs.ai.knowledge_policy import (
    employee_can_manage_categories,
    employee_can_read_knowledge,
    employee_can_write_knowledge,
    require_knowledge_create,
)
from chatballs.ai.knowledge_policy_test_base import KnowledgePolicyTestBase
from chatballs.ai.models import Knowledge
from chatballs.ai.selectors import (
    knowledge_for_employee,
    writable_knowledge_for_employee,
)


class KnowledgePolicyTests(KnowledgePolicyTestBase):
    def _all_ids(self) -> set[int]:
        return {
            self.shared.id,
            self.sales_only.id,
            self.support_only.id,
            self.disabled.id,
        }

    def test_read_policy_is_tenant_safe_and_role_based(self) -> None:
        for context in (self.owner_context, self.admin_context):
            visible_ids = set(
                knowledge_for_employee(context=context).values_list("id", flat=True)
            )
            self.assertEqual(visible_ids, self._all_ids())
        self.assertEqual(
            list(knowledge_for_employee(context=self.employee_context)), []
        )
        self.assertFalse(
            employee_can_read_knowledge(
                context=self.employee_context, knowledge=self.shared
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

    def test_write_policy_is_role_based(self) -> None:
        admin_writable_ids = set(
            writable_knowledge_for_employee(context=self.admin_context).values_list(
                "id", flat=True
            )
        )
        self.assertEqual(admin_writable_ids, self._all_ids())
        self.assertEqual(
            list(writable_knowledge_for_employee(context=self.employee_context)), []
        )
        self.assertTrue(
            employee_can_write_knowledge(
                context=self.owner_context, knowledge=self.shared
            )
        )
        self.assertFalse(
            employee_can_write_knowledge(
                context=self.employee_context, knowledge=self.sales_only
            )
        )
        other_knowledge = Knowledge.objects.create(
            organization=self.other_organization,
            category=self.other_category,
            title="Other tenant",
        )
        self.assertFalse(
            employee_can_write_knowledge(
                context=self.owner_context, knowledge=other_knowledge
            )
        )

    def test_create_and_category_policy_require_manage_role(self) -> None:
        require_knowledge_create(context=self.owner_context)
        require_knowledge_create(context=self.admin_context)
        with self.assertRaises(PermissionDenied):
            require_knowledge_create(context=self.employee_context)
        self.assertTrue(employee_can_manage_categories(context=self.owner_context))
        self.assertTrue(employee_can_manage_categories(context=self.admin_context))
        self.assertFalse(
            employee_can_manage_categories(context=self.employee_context)
        )
