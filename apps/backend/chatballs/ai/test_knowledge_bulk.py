import json

from django.test import TestCase

from chatballs.ai.knowledge_categories import create_category
from chatballs.ai.knowledge_services import KnowledgeInput, create_knowledge
from chatballs.ai.models import AIAgent, AIAgentStatus
from chatballs.channels.models import Channel
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.testing import TenantAPIClient, system_tenant_context


class KnowledgeBulkApiTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_owner(
            email="owner@example.com",
            password="temporary-password",
        )
        self.organization = result.organization
        self.context = system_tenant_context(self.organization)
        self.source = create_category(
            context=self.context,
            name="Source",
            sort_order=10,
        )
        self.target = create_category(
            context=self.context,
            name="Target",
            sort_order=20,
        )
        self.first = self._knowledge("First")
        self.second = self._knowledge("Second")
        self.client = TenantAPIClient()
        self.client.login(
            username="owner@example.com",
            password="temporary-password",
        )

    def _knowledge(
        self,
        title: str,
        *,
        category_id: int | None = None,
        is_enabled: bool = True,
    ):
        return create_knowledge(
            context=self.context,
            data=KnowledgeInput(
                title=title,
                description="",
                content=f"{title} content",
                is_enabled=is_enabled,
                category_id=category_id or self.source.id,
            ),
        )

    def _post(self, path: str, payload: dict[str, object]):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_bulk_move_is_atomic_when_one_id_is_unknown(self) -> None:
        response = self._post(
            "/api/v1/ai/knowledge/bulk/move/",
            {
                "knowledgeIds": [self.first.id, 999999, self.second.id],
                "categoryId": self.target.id,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual(self.first.category_id, self.source.id)
        self.assertEqual(self.second.category_id, self.source.id)

    def test_bulk_move_updates_all_selected_knowledge(self) -> None:
        response = self._post(
            "/api/v1/ai/knowledge/bulk/move/",
            {
                "knowledgeIds": [self.second.id, self.first.id],
                "categoryId": self.target.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated"], 2)
        self.assertEqual(
            set(
                type(self.first)
                .objects.filter(
                    id__in=[self.first.id, self.second.id],
                    category=self.target,
                )
                .values_list("id", flat=True)
            ),
            {self.first.id, self.second.id},
        )


class AgentCategoryKnowledgeSelectionTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_owner(
            email="owner@example.com",
            password="temporary-password",
        )
        self.organization = result.organization
        self.context = system_tenant_context(self.organization)
        self.category = create_category(
            context=self.context,
            name="Selection",
        )
        self.channel = Channel.objects.create(
            organization=self.organization,
            code="category-sales",
            name="Category sales",
        )
        self.agent = AIAgent.objects.create(
            channel=self.channel,
            name="Category agent",
            status=AIAgentStatus.ACTIVE,
        )
        self.existing = self._knowledge("Existing")
        self.agent.knowledge_items.add(self.existing)
        self.shared = self._knowledge("Shared", category_id=self.category.id)
        self.disabled = self._knowledge(
            "Disabled",
            category_id=self.category.id,
            is_enabled=False,
        )
        self.client = TenantAPIClient()
        self.client.login(
            username="owner@example.com",
            password="temporary-password",
        )

    def _knowledge(
        self,
        title: str,
        *,
        category_id: int | None = None,
        is_enabled: bool = True,
    ):
        return create_knowledge(
            context=self.context,
            data=KnowledgeInput(
                title=title,
                description="",
                content=title,
                is_enabled=is_enabled,
                category_id=category_id,
            ),
        )

    def test_selection_adds_only_current_category_items(self) -> None:
        response = self.client.post(
            f"/api/v1/ai/agents/{self.agent.id}/knowledge/select-category/",
            data=json.dumps({"categoryId": self.category.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()["addedKnowledgeIds"]),
            {self.shared.id, self.disabled.id},
        )
        self.assertEqual(
            set(self.agent.knowledge_items.values_list("id", flat=True)),
            {self.existing.id, self.shared.id, self.disabled.id},
        )
        future = self._knowledge("Future", category_id=self.category.id)
        self.assertFalse(self.agent.knowledge_items.filter(id=future.id).exists())
