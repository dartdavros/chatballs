"""Список агентов отдаётся страницами, поиск и группа — параметры запроса."""

from django.test import TestCase

from chatballs.channels.models import Channel
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.models import Organization
from chatballs.testing import TenantAPIClient as APIClient


class AgentListPaginationTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.group = EmployeeGroup.objects.create(
            organization=self.organization, name="Вечерняя смена"
        )
        self.channels = [
            Channel.objects.create(
                organization=self.organization,
                code=f"agent-{index:02d}",
                name=f"Агент {index:02d}",
                group=self.group if index < 4 else None,
            )
            for index in range(25)
        ]
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")

    def _page(self, query: str = "") -> dict:
        response = self.client.get(f"/api/v1/agents/{query}")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_first_page_is_bounded(self) -> None:
        page = self._page()
        total = Channel.objects.filter(organization=self.organization).count()
        self.assertEqual(len(page["items"]), 20)
        self.assertEqual(page["total"], total)

    def test_pages_cover_the_set_without_repeats(self) -> None:
        total = self._page()["total"]
        seen: list[int] = []
        for number in range(1, -(-total // 20) + 1):
            seen += [item["id"] for item in self._page(f"?page={number}")["items"]]
        self.assertEqual(len(set(seen)), total)

    def test_group_filter_is_applied_before_the_page(self) -> None:
        self.assertEqual(self._page(f"?group={self.group.id}")["total"], 4)

    def test_search_is_applied_before_the_page(self) -> None:
        self.assertEqual(self._page("?q=Агент 07")["total"], 1)
        self.assertEqual(self._page("?q=agent-07")["total"], 1)
