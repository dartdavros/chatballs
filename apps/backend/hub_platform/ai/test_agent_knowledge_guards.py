import json

from django.test import TestCase

from hub_platform.ai.knowledge_services import KnowledgeInput, create_knowledge
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.models import AIAgent, AIAgentStatus
from hub_platform.ai.retrieval import lexical_search, semantic_search
from hub_platform.ai.runtime import knowledge_catalog
from hub_platform.channels.models import Channel
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.testing import TenantAPIClient, system_tenant_context


class AgentKnowledgeAssignmentTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_edevs_owner(
            email="owner@edevs.tech",
            password="temporary-password",
        )
        self.organization = result.organization
        self.sales = result.sales_department
        self.support = result.support_department
        self.context = system_tenant_context(self.organization)
        self.shared = create_knowledge(
            context=self.context,
            data=KnowledgeInput(
                title="Shared",
                description="",
                content="Shared policy",
                is_enabled=True,
            ),
        )
        self.support_only = create_knowledge(
            context=self.context,
            data=KnowledgeInput(
                title="Support only",
                description="",
                content="Support procedure",
                is_enabled=True,
                visibility=KnowledgeVisibility.DEPARTMENTS,
                department_ids=(self.support.id,),
            ),
        )
        self.sales_channel = Channel.objects.create(
            organization=self.organization,
            code="sales-agent",
            name="Sales",
            department=self.sales,
        )
        self.support_channel = Channel.objects.create(
            organization=self.organization,
            code="support-agent",
            name="Support",
            department=self.support,
        )
        self.no_department_channel = Channel.objects.create(
            organization=self.organization,
            code="company-agent",
            name="Company",
        )
        self.client = TenantAPIClient()
        self.client.login(
            username="owner@edevs.tech",
            password="temporary-password",
        )

    def _create(self, channel: Channel, knowledge_ids: list[int]):
        return self.client.post(
            "/api/v1/ai/agents/",
            data=json.dumps({"channel": channel.code, "knowledgeIds": knowledge_ids}),
            content_type="application/json",
        )

    def test_create_rejects_entire_mixed_department_selection(self) -> None:
        response = self._create(
            self.sales_channel,
            [self.shared.id, self.support_only.id],
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(AIAgent.objects.filter(channel=self.sales_channel).exists())

    def test_support_agent_accepts_support_and_organization_knowledge(self) -> None:
        response = self._create(
            self.support_channel,
            [self.shared.id, self.support_only.id],
        )

        self.assertEqual(response.status_code, 201)
        agent = AIAgent.objects.get(channel=self.support_channel)
        self.assertEqual(
            set(agent.knowledge_items.values_list("id", flat=True)),
            {self.shared.id, self.support_only.id},
        )

    def test_channel_without_department_accepts_only_organization_knowledge(
        self,
    ) -> None:
        denied = self._create(
            self.no_department_channel,
            [self.support_only.id],
        )

        self.assertEqual(denied.status_code, 400)
        self.assertFalse(AIAgent.objects.filter(channel=self.no_department_channel).exists())
        allowed = self._create(self.no_department_channel, [self.shared.id])
        self.assertEqual(allowed.status_code, 201)

    def test_update_rolls_back_agent_fields_and_selection_on_invalid_id(self) -> None:
        agent = AIAgent.objects.create(
            channel=self.sales_channel,
            name="Original",
            status=AIAgentStatus.ACTIVE,
        )
        agent.knowledge_items.add(self.shared)

        response = self.client.patch(
            f"/api/v1/ai/agents/{agent.id}/update/",
            data=json.dumps(
                {
                    "name": "Changed",
                    "knowledgeIds": [self.shared.id, self.support_only.id],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        agent.refresh_from_db()
        self.assertEqual(agent.name, "Original")
        self.assertEqual(
            list(agent.knowledge_items.values_list("id", flat=True)),
            [self.shared.id],
        )


class AgentKnowledgeRuntimeDefenseTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_edevs_owner(
            email="owner@edevs.tech",
            password="temporary-password",
        )
        self.context = system_tenant_context(result.organization)
        self.shared = create_knowledge(
            context=self.context,
            data=KnowledgeInput(
                title="Shared runtime",
                description="Allowed catalog entry",
                content="common runtime phrase",
                is_enabled=True,
            ),
        )
        self.support_only = create_knowledge(
            context=self.context,
            data=KnowledgeInput(
                title="Support secret",
                description="Must stay hidden",
                content="secret support phrase",
                is_enabled=True,
                visibility=KnowledgeVisibility.DEPARTMENTS,
                department_ids=(result.support_department.id,),
            ),
        )
        channel = Channel.objects.create(
            organization=result.organization,
            code="runtime-sales",
            name="Runtime sales",
            department=result.sales_department,
        )
        self.agent = AIAgent.objects.create(
            channel=channel,
            name="Runtime agent",
            status=AIAgentStatus.ACTIVE,
        )
        # Simulate a historical/direct-DB invalid assignment.
        self.agent.knowledge_items.add(self.shared, self.support_only)

    def test_catalog_excludes_incompatible_selected_knowledge(self) -> None:
        catalog = knowledge_catalog(self.agent)

        self.assertIn(self.shared.title, catalog)
        self.assertNotIn(self.support_only.title, catalog)

    def test_lexical_retrieval_excludes_incompatible_fragment(self) -> None:
        results = lexical_search(self.agent, "secret support", limit=10)

        self.assertNotIn(
            self.support_only.id,
            {fragment.knowledge_id for fragment in results},
        )

    def test_semantic_retrieval_excludes_incompatible_fragment(self) -> None:
        query_vector = list(self.support_only.fragments.first().embedding)
        results = semantic_search(self.agent, query_vector, limit=10)

        self.assertNotIn(
            self.support_only.id,
            {fragment.knowledge_id for fragment in results},
        )

    def test_disabled_selected_knowledge_is_excluded_everywhere(self) -> None:
        self.shared.is_enabled = False
        self.shared.save(update_fields=["is_enabled"])

        self.assertNotIn(self.shared.title, knowledge_catalog(self.agent))
        self.assertEqual(lexical_search(self.agent, "common runtime", limit=10), [])
        vector = list(self.shared.fragments.first().embedding)
        self.assertEqual(semantic_search(self.agent, vector, limit=10), [])
