from hub_platform.ai.knowledge_policy import knowledge_is_available_to_agent
from hub_platform.ai.knowledge_categories import create_category
from hub_platform.ai.knowledge_policy_test_base import KnowledgePolicyTestBase
from hub_platform.ai.models import AIAgent
from hub_platform.ai.selectors import (
    KnowledgeFilters,
    agent_for_employee,
    agents_for_employee,
    apply_knowledge_filters,
    category_tree_for_employee,
    channel_for_ai_capability,
    knowledge_available_to_agent,
    knowledge_for_employee,
)
from hub_platform.channels.models import Channel


class KnowledgeSelectorTests(KnowledgePolicyTestBase):
    def test_filters_run_on_the_authorized_queryset(self) -> None:
        base = knowledge_for_employee(context=self.sales_context)
        search_ids = set(
            apply_knowledge_filters(
                base, KnowledgeFilters(search="support")
            ).values_list("id", flat=True)
        )
        self.assertEqual(search_ids, {self.multi_department.id})
        disabled_ids = set(
            apply_knowledge_filters(
                base, KnowledgeFilters(is_enabled=False)
            ).values_list("id", flat=True)
        )
        self.assertEqual(disabled_ids, {self.disabled_sales.id})
        support_filter_ids = set(
            apply_knowledge_filters(
                base, KnowledgeFilters(department_id=self.support.id)
            ).values_list("id", flat=True)
        )
        self.assertEqual(support_filter_ids, {self.multi_department.id})

    def test_category_counts_are_computed_after_authorization(self) -> None:
        child = create_category(
            context=self.system_context,
            parent=self.products,
            name="Nested",
        )
        nested = self._knowledge("Nested sales", "Nested content")
        nested.category = child
        nested.save(update_fields=["category"])
        self._scope(nested, self.sales)

        categories = category_tree_for_employee(context=self.sales_context)
        by_id = {category.id: category for category in categories}
        self.assertEqual(by_id[self.products.id].knowledge_count, 5)
        self.assertEqual(by_id[child.id].knowledge_count, 1)
        self.assertLess(categories.index(self.products), categories.index(child))

    def test_agent_selector_and_policy_use_channel_department(self) -> None:
        sales_channel = Channel.objects.create(
            organization=self.organization,
            department=self.sales,
            code="sales-ai",
            name="Sales AI",
        )
        sales_agent = AIAgent.objects.create(channel=sales_channel, name="Sales agent")
        allowed_ids = set(
            knowledge_available_to_agent(agent=sales_agent).values_list("id", flat=True)
        )
        self.assertEqual(
            allowed_ids,
            {
                self.shared.id,
                self.sales_only.id,
                self.multi_department.id,
                self.disabled_sales.id,
            },
        )
        self.assertTrue(
            knowledge_is_available_to_agent(
                knowledge=self.sales_only, agent=sales_agent
            )
        )
        self.assertFalse(
            knowledge_is_available_to_agent(
                knowledge=self.support_only, agent=sales_agent
            )
        )

        support_channel = Channel.objects.create(
            organization=self.organization,
            department=self.support,
            code="support-ai",
            name="Support AI",
        )
        support_agent = AIAgent.objects.create(
            channel=support_channel, name="Support agent"
        )
        self.assertEqual(
            list(
                agents_for_employee(
                    context=self.sales_context, capability="ai.view"
                ).values_list("id", flat=True)
            ),
            [sales_agent.id],
        )
        self.assertEqual(
            agent_for_employee(
                context=self.sales_context,
                agent_id=sales_agent.id,
                capability="ai.view",
            ),
            sales_agent,
        )
        with self.assertRaises(AIAgent.DoesNotExist):
            agent_for_employee(
                context=self.sales_context,
                agent_id=support_agent.id,
                capability="ai.view",
            )
        self.assertEqual(
            channel_for_ai_capability(
                context=self.sales_context,
                channel_code=sales_channel.code,
                capability="ai.manage",
            ),
            sales_channel,
        )
        with self.assertRaises(Channel.DoesNotExist):
            channel_for_ai_capability(
                context=self.sales_context,
                channel_code=support_channel.code,
                capability="ai.manage",
            )

        no_department_channel = Channel.objects.create(
            organization=self.organization,
            code="shared-ai",
            name="Shared AI",
        )
        no_department_agent = AIAgent.objects.create(
            channel=no_department_channel, name="Shared agent"
        )
        self.assertEqual(
            set(
                knowledge_available_to_agent(
                    agent=no_department_agent
                ).values_list("id", flat=True)
            ),
            {self.shared.id},
        )
