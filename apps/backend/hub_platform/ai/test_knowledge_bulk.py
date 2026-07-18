import json

from django.test import TestCase

from hub_platform.ai.knowledge_categories import create_category
from hub_platform.ai.knowledge_services import KnowledgeInput, create_knowledge
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.models import AIAgent, AIAgentStatus
from hub_platform.channels.models import Channel
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.testing import TenantAPIClient, system_tenant_context


class KnowledgeBulkApiTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_edevs_owner(
            email="owner@edevs.tech",
            password="temporary-password",
        )
        self.organization = result.organization
        self.sales = result.sales_department
        self.support = result.support_department
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
            username="owner@edevs.tech",
            password="temporary-password",
        )

    def _knowledge(
        self,
        title: str,
        *,
        category_id: int | None = None,
        visibility: str = KnowledgeVisibility.ORGANIZATION,
        department_ids: tuple[int, ...] = (),
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
                visibility=visibility,
                department_ids=department_ids,
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

    def test_bulk_visibility_conflict_rolls_back_every_item(self) -> None:
        channel = Channel.objects.create(
            organization=self.organization,
            code="bulk-sales",
            name="Bulk sales",
            department=self.sales,
        )
        agent = AIAgent.objects.create(
            channel=channel,
            name="Bulk sales agent",
            status=AIAgentStatus.ACTIVE,
        )
        agent.knowledge_items.add(self.first)

        response = self._post(
            "/api/v1/ai/knowledge/bulk/visibility/",
            {
                "knowledgeIds": [self.first.id, self.second.id],
                "visibility": KnowledgeVisibility.DEPARTMENTS,
                "departmentIds": [self.support.id],
            },
        )

        self.assertEqual(response.status_code, 409)
        for knowledge in (self.first, self.second):
            knowledge.refresh_from_db()
            self.assertEqual(knowledge.visibility, KnowledgeVisibility.ORGANIZATION)
            self.assertFalse(knowledge.department_links.exists())

    def test_bulk_visibility_replaces_all_links_without_reindexing(self) -> None:
        fragment_ids = {
            self.first.id: list(self.first.fragments.values_list("id", flat=True)),
            self.second.id: list(self.second.fragments.values_list("id", flat=True)),
        }

        response = self._post(
            "/api/v1/ai/knowledge/bulk/visibility/",
            {
                "knowledgeIds": [self.first.id, self.second.id],
                "visibility": KnowledgeVisibility.DEPARTMENTS,
                "departmentIds": [self.sales.id, self.support.id],
            },
        )

        self.assertEqual(response.status_code, 200)
        for knowledge in (self.first, self.second):
            knowledge.refresh_from_db()
            self.assertEqual(knowledge.visibility, KnowledgeVisibility.DEPARTMENTS)
            self.assertEqual(
                set(knowledge.department_links.values_list("department_id", flat=True)),
                {self.sales.id, self.support.id},
            )
            self.assertEqual(
                list(knowledge.fragments.values_list("id", flat=True)),
                fragment_ids[knowledge.id],
            )


class AgentCategoryKnowledgeSelectionTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_edevs_owner(
            email="owner@edevs.tech",
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
            department=result.sales_department,
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
        self.support_only = self._knowledge(
            "Support",
            category_id=self.category.id,
            visibility=KnowledgeVisibility.DEPARTMENTS,
            department_ids=(result.support_department.id,),
        )
        self.client = TenantAPIClient()
        self.client.login(
            username="owner@edevs.tech",
            password="temporary-password",
        )

    def _knowledge(
        self,
        title: str,
        *,
        category_id: int | None = None,
        visibility: str = KnowledgeVisibility.ORGANIZATION,
        department_ids: tuple[int, ...] = (),
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
                visibility=visibility,
                department_ids=department_ids,
            ),
        )

    def test_selection_adds_only_current_compatible_category_items(self) -> None:
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
