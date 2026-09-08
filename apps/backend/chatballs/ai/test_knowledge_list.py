"""Библиотека знаний: страница и фильтры на сервере.

Раньше список отдавался целиком, а ветку категорий и фильтр по агенту отбирал
браузер — значит, фильтр видел ровно то, что успело загрузиться.
"""

from django.test import TestCase

from chatballs.ai.knowledge_categories import create_category
from chatballs.ai.knowledge_services import KnowledgeInput, create_knowledge
from chatballs.ai.models import AIAgent, AIAgentStatus
from chatballs.channels.models import Channel
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.testing import TenantAPIClient, system_tenant_context

PAGE_SIZE = 25


class KnowledgeListPaginationTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = result.organization
        self.context = system_tenant_context(self.organization)
        self.root = create_category(context=self.context, name="Тарифы")
        self.child = create_category(context=self.context, name="Скидки", parent=self.root)
        self.other = create_category(context=self.context, name="Доставка")
        self.items = [
            self._knowledge(
                f"Материал {index:02d}",
                category=self.child if index < 4 else self.other,
                enabled=index != 0,
            )
            for index in range(30)
        ]
        channel = Channel.objects.create(
            organization=self.organization, code="agent-a", name="Агент A"
        )
        self.agent = AIAgent.objects.create(
            channel=channel, name="Агент A", status=AIAgentStatus.ACTIVE
        )
        self.attached = self.items[:3]
        self.agent.knowledge_items.set(self.attached)
        self.client = TenantAPIClient()
        self.client.force_authenticate(result.owner)

    def _knowledge(self, title: str, *, category, enabled: bool = True):
        return create_knowledge(
            context=self.context,
            data=KnowledgeInput(
                title=title,
                description="",
                content=f"{title} — текст",
                is_enabled=enabled,
                category_id=category.id,
            ),
        )

    def _page(self, query: str = "") -> dict:
        response = self.client.get(f"/api/v1/ai/knowledge/{query}")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_first_page_is_bounded(self) -> None:
        page = self._page()
        self.assertEqual(len(page["items"]), PAGE_SIZE)
        self.assertEqual(page["total"], 30)
        self.assertEqual(page["pageCount"], 2)

    def test_pages_cover_the_library_without_repeats(self) -> None:
        seen = [item["id"] for item in self._page()["items"]]
        seen += [item["id"] for item in self._page("?page=2")["items"]]
        self.assertEqual(len(set(seen)), 30)

    def test_category_filter_covers_the_branch(self) -> None:
        # Выбран родитель — материалы вложенного раздела тоже попадают.
        self.assertEqual(self._page(f"?category={self.root.id}")["total"], 4)

    def test_agent_filter_is_applied_before_the_page(self) -> None:
        page = self._page(f"?agent={self.agent.id}")
        self.assertEqual(page["total"], len(self.attached))

    def test_agent_filter_does_not_shrink_counters(self) -> None:
        # Счётчик «прикреплено к N агентам» считается подзапросом: фильтр по
        # агенту идёт по той же связи и не должен его урезать.
        item = self._page(f"?agent={self.agent.id}")["items"][0]
        self.assertEqual(item["agentsCount"], 1)
        self.assertEqual(item["agentIds"], [self.agent.id])

    def test_enabled_and_search_filters_are_applied_before_the_page(self) -> None:
        self.assertEqual(self._page("?isEnabled=false")["total"], 1)
        self.assertEqual(self._page("?search=Материал 07")["total"], 1)

    def test_detail_lists_attached_agents(self) -> None:
        response = self.client.get(f"/api/v1/ai/knowledge/{self.attached[0].id}/")
        self.assertEqual(response.status_code, 200)
        agents = response.json()["knowledge"]["agents"]
        self.assertEqual([agent["id"] for agent in agents], [self.agent.id])
        self.assertEqual(agents[0]["aiStatus"], AIAgentStatus.ACTIVE)


class AgentDirectoryTests(TestCase):
    """Справочник агентов для выпадающих выборов: имена и счётчики, не карточки."""

    def setUp(self) -> None:
        result = bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = result.organization
        self.context = system_tenant_context(self.organization)
        category = create_category(context=self.context, name="Общее")
        knowledge = create_knowledge(
            context=self.context,
            data=KnowledgeInput(
                title="Возврат",
                description="",
                content="Условия возврата",
                is_enabled=True,
                category_id=category.id,
            ),
        )
        channel = Channel.objects.create(
            organization=self.organization, code="agent-b", name="Агент B"
        )
        agent = AIAgent.objects.create(
            channel=channel, name="Агент B", status=AIAgentStatus.ACTIVE
        )
        agent.knowledge_items.add(knowledge)
        self.agent = agent
        self.client = TenantAPIClient()
        self.client.force_authenticate(result.owner)

    def test_directory_returns_compact_rows_with_counts(self) -> None:
        response = self.client.get("/api/v1/agents/directory/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        row = next(item for item in payload["items"] if item["aiAgentId"] == self.agent.id)
        self.assertEqual(row["name"], "Агент B")
        self.assertEqual(row["knowledgeCount"], 1)
        self.assertFalse(payload["hasMore"])

    def test_directory_search_narrows_rows(self) -> None:
        payload = self.client.get("/api/v1/agents/directory/?q=Агент B").json()
        self.assertEqual([item["name"] for item in payload["items"]], ["Агент B"])
