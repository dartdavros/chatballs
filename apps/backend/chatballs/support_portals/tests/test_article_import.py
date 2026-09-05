from chatballs.support_portals.models import PortalArticle
from chatballs.support_portals.tests.base import SupportPortalTestCase


class SupportPortalArticleImportTests(SupportPortalTestCase):
    def _category(
        self,
        portal_id: int,
        name: str,
        slug: str,
        parent_id: int | None = None,
    ) -> int:
        payload = {"slug": slug, "name": name}
        if parent_id is not None:
            payload["parentId"] = parent_id
        response = self.client.post(
            f"/api/v1/support/portals/{portal_id}/categories/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["category"]["id"]

    def _import(self, portal_id: int, articles: list[object]):
        return self.client.post(
            f"/api/v1/support/portals/{portal_id}/articles/import/",
            data={"articles": articles},
            format="json",
        )

    def test_import_creates_new_article_from_category_path(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        parent = self._category(portal_id, "Возврат", "returns")
        self._category(portal_id, "Оформление", "checkout", parent_id=parent)

        response = self._import(
            portal_id,
            [
                {
                    "slug": "vozvrat-tovara",
                    "categoryPath": ["Возврат", "Оформление"],
                    "title": "Как оформить возврат",
                    "summary": "Короткое описание",
                    "content": "Шаги оформления возврата.",
                }
            ],
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["created"], 1)
        article = PortalArticle.objects.get(slug="vozvrat-tovara")
        self.assertEqual(article.category.name, "Оформление")
        self.assertEqual(article.revisions.count(), 1)
        self.assertEqual(article.revisions.first().title, "Как оформить возврат")

    def test_import_updates_existing_article_by_slug_with_new_revision(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        self._category(portal_id, "Возврат", "returns")

        self._import(
            portal_id,
            [
                {
                    "slug": "garantiya",
                    "categoryPath": ["Возврат"],
                    "title": "Гарантия",
                    "content": "Версия 1",
                }
            ],
        )

        response = self._import(
            portal_id,
            [
                {
                    "slug": "garantiya",
                    "categoryPath": ["Возврат"],
                    "title": "Гарантия",
                    "content": "Версия 2",
                }
            ],
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["updated"], 1)
        self.assertEqual(body["created"], 0)
        article = PortalArticle.objects.get(slug="garantiya")
        self.assertEqual(article.revisions.count(), 2)
        self.assertEqual(article.revisions.order_by("-revision").first().content, "Версия 2")

    def test_import_marks_unchanged_article_when_content_matches(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        self._category(portal_id, "Возврат", "returns")

        document = {
            "slug": "neizmennyj",
            "categoryPath": ["Возврат"],
            "title": "Без изменений",
            "content": "Текст",
        }
        self._import(portal_id, [document])
        response = self._import(portal_id, [document])

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["unchanged"], 1)
        article = PortalArticle.objects.get(slug="neizmennyj")
        self.assertEqual(article.revisions.count(), 1)

    def test_import_reports_failed_document_for_unknown_category_path(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        self._category(portal_id, "Возврат", "returns")

        response = self._import(
            portal_id,
            [
                {
                    "slug": "problemnyj",
                    "categoryPath": ["Не существует"],
                    "title": "Проблема",
                    "content": "Текст",
                }
            ],
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["created"], 0)
        self.assertEqual(len(body["failed"]), 1)
        self.assertEqual(body["failed"][0]["slug"], "problemnyj")
        self.assertFalse(PortalArticle.objects.filter(slug="problemnyj").exists())

    def test_import_rejects_empty_articles_list(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        response = self._import(portal_id, [])
        self.assertEqual(response.status_code, 400)
