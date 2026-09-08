"""Контракт постраничных ответов: границы, потолки и поведение на краю набора."""

from django.http import QueryDict
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from chatballs.api.pagination import (
    MAX_PAGE_SIZE,
    SortKey,
    cursor_id,
    page_payload,
    paginate,
    window,
    window_size,
)
from chatballs.conversations.models import Contact
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization


def params(query: str = "") -> QueryDict:
    return QueryDict(query)


class PaginateTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        for index in range(45):
            Contact.objects.create(
                organization=self.organization, name=f"Контакт {index:02d}"
            )
        self.queryset = Contact.objects.filter(
            organization=self.organization
        ).order_by("name")

    def test_first_page_reports_whole_set(self) -> None:
        page = paginate(self.queryset, params("pageSize=20"))
        self.assertEqual(len(page.items), 20)
        self.assertEqual(page.page, 1)
        self.assertEqual(page.total, 45)
        self.assertEqual(page.page_count, 3)

    def test_last_page_holds_remainder(self) -> None:
        page = paginate(self.queryset, params("page=3&pageSize=20"))
        self.assertEqual(len(page.items), 5)

    def test_page_beyond_set_falls_back_to_last(self) -> None:
        # Записи могли удалить из-под открытой страницы — список не должен
        # становиться пустым.
        page = paginate(self.queryset, params("page=99&pageSize=20"))
        self.assertEqual(page.page, 3)
        self.assertEqual(len(page.items), 5)

    def test_page_size_is_capped(self) -> None:
        page = paginate(self.queryset, params(f"pageSize={MAX_PAGE_SIZE * 10}"))
        self.assertEqual(page.page_size, MAX_PAGE_SIZE)

    def test_empty_set_still_has_one_page(self) -> None:
        page = paginate(Contact.objects.none(), params())
        self.assertEqual(page.page_count, 1)
        self.assertEqual(page.total, 0)

    def test_broken_params_are_rejected(self) -> None:
        for query in ("page=abc", "page=0", "pageSize=-1", "pageSize=x"):
            with self.subTest(query=query):
                with self.assertRaises(ValidationError):
                    paginate(self.queryset, params(query))

    def test_payload_carries_everything_the_footer_needs(self) -> None:
        payload = page_payload(
            paginate(self.queryset, params("pageSize=20")), lambda c: {"id": c.id}
        )
        self.assertEqual(
            set(payload), {"items", "page", "pageSize", "total", "pageCount"}
        )


class WindowTests(TestCase):
    """Окно по курсору: без дублей и пропусков на границах."""

    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.contacts = [
            Contact.objects.create(
                organization=self.organization, name=f"Контакт {index:02d}"
            )
            for index in range(25)
        ]
        self.queryset = Contact.objects.filter(organization=self.organization)
        self.keys = (SortKey("id"),)

    def test_window_reports_more(self) -> None:
        page = window(self.queryset, keys=self.keys, limit=10)
        self.assertEqual(len(page.items), 10)
        self.assertTrue(page.has_more)
        self.assertEqual(page.cursor, page.items[-1].id)

    def test_cursor_walks_whole_set(self) -> None:
        seen: list[int] = []
        page = window(self.queryset, keys=self.keys, limit=10)
        seen += [item.id for item in page.items]
        while page.has_more:
            page = window(self.queryset, keys=self.keys, limit=10, after=page.cursor)
            seen += [item.id for item in page.items]
        self.assertEqual(seen, sorted((c.id for c in self.contacts), reverse=True))

    def test_last_window_has_no_cursor(self) -> None:
        page = window(self.queryset, keys=self.keys, limit=100)
        self.assertFalse(page.has_more)
        self.assertIsNone(page.cursor)

    def test_missing_anchor_returns_head(self) -> None:
        page = window(self.queryset, keys=self.keys, limit=5, after=10_000_000)
        self.assertEqual(len(page.items), 5)

    def test_window_size_and_cursor_params_are_validated(self) -> None:
        self.assertEqual(window_size(params("limit=7")), 7)
        self.assertIsNone(cursor_id(params()))
        self.assertEqual(cursor_id(params("cursor=12")), 12)
        with self.assertRaises(ValidationError):
            cursor_id(params("cursor=abc"))
