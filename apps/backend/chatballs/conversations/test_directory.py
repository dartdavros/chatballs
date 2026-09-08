"""Справочник выбора ответственного: ограниченная выдача и поиск на сервере."""

from django.test import TestCase

from chatballs.conversations.chat_extras_views import DIRECTORY_LIMIT
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.testing import TenantAPIClient as APIClient


class ConversationDirectoryTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        for index in range(DIRECTORY_LIMIT + 10):
            user = HumanUser.objects.create_user(
                email=f"member{index:03d}@example.com",
                password="Password-123",
                full_name=f"Сотрудник {index:03d}",
            )
            OrganizationMembership.objects.create(
                user=user,
                organization=self.organization,
                role=EmployeeRole.EMPLOYEE,
                position_title="Оператор",
            )
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")

    def _directory(self, query: str = "") -> dict:
        response = self.client.get(f"/api/v1/conversations/directory/{query}")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_employees_are_bounded_and_report_the_rest(self) -> None:
        payload = self._directory()
        self.assertEqual(len(payload["employees"]), DIRECTORY_LIMIT)
        self.assertTrue(payload["hasMoreEmployees"])

    def test_search_finds_colleague_outside_the_first_rows(self) -> None:
        # Именно ради этого случая в выборе и появляется строка поиска.
        payload = self._directory("?q=Сотрудник 057")
        self.assertEqual([item["name"] for item in payload["employees"]], ["Сотрудник 057"])
        self.assertFalse(payload["hasMoreEmployees"])

    def test_search_matches_email(self) -> None:
        payload = self._directory("?q=member042@")
        self.assertEqual(len(payload["employees"]), 1)

    def test_groups_are_returned_as_before(self) -> None:
        self.assertIn("groups", self._directory())
