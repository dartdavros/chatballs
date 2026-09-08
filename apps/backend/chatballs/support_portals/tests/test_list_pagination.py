"""Списки порталов и библиотеки статей отдаются страницами."""

from chatballs.support_portals.models import (
    PortalArticle,
    PortalArticleRevision,
    PortalCategory,
    SupportPortal,
)
from chatballs.support_portals.statuses import ArticleStatus, PortalStatus
from chatballs.support_portals.tests.base import SupportPortalTestCase


class PortalListPaginationTests(SupportPortalTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.portals = [
            SupportPortal.objects.create(
                organization=self.organization,
                slug=f"portal-{index:02d}",
                hosted_domain=f"portal-{index:02d}.example.test",
                name=f"Портал {index:02d}",
            )
            for index in range(25)
        ]
        self.archived = self.portals[0]
        self.archived.status = PortalStatus.ARCHIVED
        self.archived.save(update_fields=["status"])

    def _page(self, query: str = "") -> dict:
        response = self.client.get(f"/api/v1/support/portals/{query}")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_first_page_is_bounded(self) -> None:
        page = self._page()
        self.assertEqual(len(page["items"]), 20)
        self.assertEqual(page["total"], 25)
        self.assertEqual(page["pageCount"], 2)

    def test_archived_portals_go_last(self) -> None:
        # Архивный портал не должен попасть на первую страницу впереди действующих.
        last = self._page("?page=2")["items"][-1]
        self.assertEqual(last["id"], self.archived.id)

    def test_status_filter_is_applied_before_the_page(self) -> None:
        page = self._page("?status=ARCHIVED")
        self.assertEqual(page["total"], 1)

    def test_search_is_applied_before_the_page(self) -> None:
        self.assertEqual(self._page("?q=Портал 07")["total"], 1)
        self.assertEqual(self._page("?q=portal-07.example.test")["total"], 1)


class ArticleLibraryPaginationTests(SupportPortalTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.portal = SupportPortal.objects.create(
            organization=self.organization,
            slug="library",
            hosted_domain="library.example.test",
            name="Библиотека",
        )
        self.root = PortalCategory.objects.create(
            organization=self.organization, portal=self.portal, slug="root", name="Раздел"
        )
        self.child = PortalCategory.objects.create(
            organization=self.organization,
            portal=self.portal,
            parent=self.root,
            slug="child",
            name="Подраздел",
        )
        self.other = PortalCategory.objects.create(
            organization=self.organization, portal=self.portal, slug="other", name="Другое"
        )
        for index in range(30):
            category = self.child if index < 4 else self.other
            article = PortalArticle.objects.create(
                organization=self.organization,
                portal=self.portal,
                category=category,
                slug=f"article-{index:02d}",
                locale="en" if index < 3 else "ru",
                status=ArticleStatus.PUBLISHED if index < 2 else ArticleStatus.DRAFT,
            )
            PortalArticleRevision.objects.create(
                organization=self.organization,
                article=article,
                revision=1,
                title=f"Статья {index:02d}",
                summary="Короткое описание",
                content="Текст",
            )

    def _page(self, query: str = "") -> dict:
        response = self.client.get(
            f"/api/v1/support/portals/{self.portal.id}/articles/{query}"
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_first_page_is_bounded(self) -> None:
        page = self._page()
        self.assertEqual(len(page["items"]), 25)
        self.assertEqual(page["total"], 30)
        self.assertEqual(page["pageCount"], 2)

    def test_category_filter_covers_the_subtree(self) -> None:
        # Выбран родитель — статьи из вложенного раздела тоже попадают.
        self.assertEqual(self._page(f"?category={self.root.id}")["total"], 4)

    def test_locale_and_status_filters_are_applied_before_the_page(self) -> None:
        self.assertEqual(self._page("?locale=en")["total"], 3)
        self.assertEqual(self._page("?status=PUBLISHED")["total"], 2)

    def test_search_matches_slug_and_latest_revision(self) -> None:
        self.assertEqual(self._page("?q=article-07")["total"], 1)
        self.assertEqual(self._page("?q=Статья 07")["total"], 1)
