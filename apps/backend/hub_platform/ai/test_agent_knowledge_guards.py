import json

from django.test import TestCase

from hub_platform.ai.knowledge_categories import ensure_uncategorized_category
from hub_platform.ai.knowledge_services import KnowledgeInput, create_knowledge
from hub_platform.ai.models import AIAgent, AIAgentStatus
from hub_platform.ai.retrieval import lexical_search, semantic_search
from hub_platform.ai.runtime import knowledge_catalog
from hub_platform.channels.models import Channel
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import Organization
from hub_platform.tenancy.context import TenantContext
from hub_platform.testing import TenantAPIClient, system_tenant_context


class AgentKnowledgeAssignmentTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_edevs_owner(
            email="owner@edevs.tech",
            password="temporary-password",
        )
        self.organization = result.organization
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
        self.second = create_knowledge(
            context=self.context,
            data=KnowledgeInput(
                title="Second",
                description="",
                content="Second procedure",
                is_enabled=True,
            ),
        )
        self.channel = Channel.objects.create(
            organization=self.organization,
            code="org-agent",
            name="Org",
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

    def test_create_accepts_organization_knowledge(self) -> None:
        response = self._create(
            self.channel,
            [self.shared.id, self.second.id],
        )

        self.assertEqual(response.status_code, 201)
        agent = AIAgent.objects.get(channel=self.channel)
        self.assertEqual(
            set(agent.knowledge_items.values_list("id", flat=True)),
            {self.shared.id, self.second.id},
        )

    def test_create_rejects_selection_with_unknown_knowledge_id(self) -> None:
        response = self._create(
            self.channel,
            [self.shared.id, 999999],
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(AIAgent.objects.filter(channel=self.channel).exists())

    def test_update_rolls_back_agent_fields_and_selection_on_invalid_id(self) -> None:
        agent = AIAgent.objects.create(
            channel=self.channel,
            name="Original",
            status=AIAgentStatus.ACTIVE,
        )
        agent.knowledge_items.add(self.shared)

        response = self.client.patch(
            f"/api/v1/ai/agents/{agent.id}/update/",
            data=json.dumps(
                {
                    "name": "Changed",
                    "knowledgeIds": [self.shared.id, 999999],
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
        self.other_organization = Organization.objects.create(
            name="Foreign",
            slug="runtime-foreign",
        )
        ensure_uncategorized_category(self.other_organization)
        self.foreign = create_knowledge(
            context=TenantContext.for_resource(self.other_organization),
            data=KnowledgeInput(
                title="Foreign secret",
                description="Must stay hidden",
                content="secret foreign phrase",
                is_enabled=True,
            ),
        )
        channel = Channel.objects.create(
            organization=result.organization,
            code="runtime-sales",
            name="Runtime sales",
        )
        self.agent = AIAgent.objects.create(
            channel=channel,
            name="Runtime agent",
            status=AIAgentStatus.ACTIVE,
        )
        self.agent.knowledge_items.add(self.shared)

    def test_cross_organization_assignment_is_rejected_by_database(self) -> None:
        # Парный триггер enforce_tenant_pair не даёт «протащить» чужое знание
        # даже прямой записью в M2M-таблицу.
        from django.db import DatabaseError, transaction

        with self.assertRaises(DatabaseError), transaction.atomic():
            self.agent.knowledge_items.add(self.foreign)

    def test_catalog_excludes_foreign_organization_knowledge(self) -> None:
        catalog = knowledge_catalog(self.agent)

        self.assertIn(self.shared.title, catalog)
        self.assertNotIn(self.foreign.title, catalog)

    def test_lexical_retrieval_excludes_foreign_fragment(self) -> None:
        results = lexical_search(self.agent, "secret foreign", limit=10)

        self.assertNotIn(
            self.foreign.id,
            {fragment.knowledge_id for fragment in results},
        )

    def test_semantic_retrieval_excludes_foreign_fragment(self) -> None:
        query_vector = list(self.foreign.fragments.first().embedding)
        results = semantic_search(self.agent, query_vector, limit=10)

        self.assertNotIn(
            self.foreign.id,
            {fragment.knowledge_id for fragment in results},
        )

    def test_disabled_selected_knowledge_is_excluded_everywhere(self) -> None:
        self.shared.is_enabled = False
        self.shared.save(update_fields=["is_enabled"])

        self.assertNotIn(self.shared.title, knowledge_catalog(self.agent))
        self.assertEqual(lexical_search(self.agent, "common runtime", limit=10), [])
        vector = list(self.shared.fragments.first().embedding)
        self.assertEqual(semantic_search(self.agent, vector, limit=10), [])
