from chatballs.ai.knowledge_categories import create_category
from chatballs.ai.knowledge_policy import knowledge_is_available_to_agent
from chatballs.ai.knowledge_policy_test_base import KnowledgePolicyTestBase
from chatballs.ai.models import AIAgent, Knowledge
from chatballs.ai.selectors import (
    KnowledgeFilters,
    agent_for_employee,
    agents_for_employee,
    apply_knowledge_filters,
    category_tree_for_employee,
    knowledge_available_to_agent,
    knowledge_for_employee,
)
from chatballs.channels.models import Channel


class KnowledgeSelectorTests(KnowledgePolicyTestBase):
    def test_filters_run_on_the_authorized_queryset(self) -> None:
        base = knowledge_for_employee(context=self.admin_context)
        search_ids = set(
            apply_knowledge_filters(
                base, KnowledgeFilters(search="support"), organization_id=self.organization.id
            ).values_list("id", flat=True)
        )
        self.assertEqual(search_ids, {self.support_only.id})
        disabled_ids = set(
            apply_knowledge_filters(
                base, KnowledgeFilters(is_enabled=False), organization_id=self.organization.id
            ).values_list("id", flat=True)
        )
        self.assertEqual(disabled_ids, {self.disabled.id})
        category_ids = set(
            apply_knowledge_filters(
                base, KnowledgeFilters(category_id=self.products.id), organization_id=self.organization.id
            ).values_list("id", flat=True)
        )
        self.assertEqual(
            category_ids,
            {
                self.shared.id,
                self.sales_only.id,
                self.support_only.id,
                self.disabled.id,
            },
        )
        employee_base = knowledge_for_employee(context=self.employee_context)
        self.assertEqual(
            list(apply_knowledge_filters(employee_base, KnowledgeFilters(), organization_id=self.organization.id)), []
        )

    def test_category_counts_are_computed_after_authorization(self) -> None:
        child = create_category(
            context=self.system_context,
            parent=self.products,
            name="Nested",
        )
        nested = self._knowledge("Nested item", "Nested content")
        nested.category = child
        nested.save(update_fields=["category"])

        categories = category_tree_for_employee(context=self.admin_context)
        by_id = {category.id: category for category in categories}
        self.assertEqual(by_id[self.products.id].knowledge_count, 5)
        self.assertEqual(by_id[child.id].knowledge_count, 1)
        self.assertLess(categories.index(self.products), categories.index(child))

        employee_categories = category_tree_for_employee(
            context=self.employee_context
        )
        employee_by_id = {category.id: category for category in employee_categories}
        self.assertEqual(employee_by_id[self.products.id].knowledge_count, 0)
        self.assertEqual(employee_by_id[child.id].knowledge_count, 0)

    def test_agent_selectors_are_organization_scoped_and_role_gated(self) -> None:
        channel = Channel.objects.create(
            organization=self.organization,
            code="org-ai",
            name="Org AI",
        )
        agent = AIAgent.objects.create(channel=channel, name="Org agent")

        allowed_ids = set(
            knowledge_available_to_agent(agent=agent).values_list("id", flat=True)
        )
        self.assertEqual(
            allowed_ids,
            {
                self.shared.id,
                self.sales_only.id,
                self.support_only.id,
                self.disabled.id,
            },
        )
        self.assertTrue(
            knowledge_is_available_to_agent(knowledge=self.sales_only, agent=agent)
        )
        other_knowledge = Knowledge.objects.create(
            organization=self.other_organization,
            category=self.other_category,
            title="Other tenant",
        )
        self.assertFalse(
            knowledge_is_available_to_agent(knowledge=other_knowledge, agent=agent)
        )

        self.assertEqual(
            list(
                agents_for_employee(
                    context=self.admin_context, capability="ai.view"
                ).values_list("id", flat=True)
            ),
            [agent.id],
        )
        self.assertEqual(
            agent_for_employee(
                context=self.admin_context,
                agent_id=agent.id,
                capability="ai.view",
            ),
            agent,
        )
        self.assertEqual(
            list(
                agents_for_employee(
                    context=self.employee_context, capability="ai.view"
                )
            ),
            [],
        )
        with self.assertRaises(AIAgent.DoesNotExist):
            agent_for_employee(
                context=self.employee_context,
                agent_id=agent.id,
                capability="ai.view",
            )
