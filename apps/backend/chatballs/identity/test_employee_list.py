"""Список сотрудников отдаётся страницами, а фильтры считает база."""

from django.test import TestCase

from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.group_models import EmployeeGroup, EmployeeGroupMember
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.testing import TenantAPIClient as APIClient


class EmployeeListPaginationTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.group = EmployeeGroup.objects.create(
            organization=self.organization, name="Ночная смена"
        )
        for index in range(44):
            user = HumanUser.objects.create_user(
                email=f"employee{index:02d}@example.com", password="Password-123"
            )
            membership = OrganizationMembership.objects.create(
                user=user,
                organization=self.organization,
                role=EmployeeRole.ADMIN if index < 5 else EmployeeRole.EMPLOYEE,
                position_title="Оператор" if index else "Руководитель поддержки",
            )
            if index < 3:
                EmployeeGroupMember.objects.create(
                    organization=self.organization, group=self.group, employee=membership
                )
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")

    def _page(self, query: str = "") -> dict:
        response = self.client.get(f"/api/v1/employees/{query}")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_first_page_is_bounded_and_reports_whole_set(self) -> None:
        page = self._page()
        total = OrganizationMembership.objects.filter(organization=self.organization).count()
        self.assertEqual(len(page["items"]), 20)
        self.assertEqual(page["total"], total)
        self.assertEqual(page["pageCount"], -(-total // 20))
        self.assertEqual(page["page"], 1)

    def test_pages_cover_the_set_without_repeats(self) -> None:
        total = OrganizationMembership.objects.filter(organization=self.organization).count()
        seen: list[int] = []
        for number in range(1, -(-total // 20) + 1):
            seen += [item["id"] for item in self._page(f"?page={number}")["items"]]
        self.assertEqual(len(seen), total)
        self.assertEqual(len(set(seen)), total)

    def test_role_filter_is_applied_before_the_page(self) -> None:
        page = self._page("?role=ADMIN")
        admins = OrganizationMembership.objects.filter(
            organization=self.organization, role=EmployeeRole.ADMIN
        ).count()
        self.assertEqual(page["total"], admins)
        self.assertTrue(all(item["role"] == "ADMIN" for item in page["items"]))

    def test_group_filter_is_applied_before_the_page(self) -> None:
        page = self._page(f"?group={self.group.id}")
        self.assertEqual(page["total"], 3)

    def test_search_covers_name_email_and_position(self) -> None:
        self.assertEqual(self._page("?q=employee07")["total"], 1)
        self.assertEqual(self._page("?q=Руководитель")["total"], 1)

    def test_search_and_role_narrow_together(self) -> None:
        page = self._page("?role=EMPLOYEE&q=employee1")
        # employee10..employee19 — десять сотрудников роли EMPLOYEE.
        self.assertEqual(page["total"], 10)
