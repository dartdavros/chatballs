from hub_platform.support_portals.tests.base import SupportPortalTestCase
from hub_platform.webchat.testing import create_web_widget


class SupportPortalContentManagementTests(SupportPortalTestCase):
    def test_article_revisions_are_preserved_and_selected_for_publish(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        category = self.client.post(
            f"/api/v1/support/portals/{portal_id}/categories/",
            {"name": "Аккаунт"},
            format="json",
        )
        self.assertEqual(category.status_code, 201, category.content)
        self.assertTrue(category.json()["category"]["slug"])
        article = self.client.post(
            f"/api/v1/support/portals/{portal_id}/articles/",
            {
                "categoryId": category.json()["category"]["id"],
                "slug": "sign-in",
                "title": "Вход",
                "summary": "Как войти",
                "content": "Версия 1",
            },
            format="json",
        )
        self.assertEqual(article.status_code, 201, article.content)
        article_id = article.json()["article"]["id"]
        revision = self.client.post(
            f"/api/v1/support/portals/{portal_id}/articles/{article_id}/revisions/",
            {"title": "Вход в аккаунт", "summary": "Как войти", "content": "Версия 2"},
            format="json",
        )
        self.assertEqual(revision.status_code, 201, revision.content)
        published = self.client.post(
            f"/api/v1/support/portals/{portal_id}/articles/{article_id}/publish/",
            {"revisionId": revision.json()["revision"]["id"]},
            format="json",
        )
        self.assertEqual(published.status_code, 200, published.content)
        body = published.json()["article"]
        self.assertEqual(len(body["revisions"]), 2)
        self.assertEqual(body["publishedRevision"]["content"], "Версия 2")

    def test_archived_portal_rejects_every_content_mutation(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        category = self.client.post(
            f"/api/v1/support/portals/{portal_id}/categories/",
            {"slug": "account", "name": "Аккаунт"},
            format="json",
        ).json()["category"]
        self.client.post(
            f"/api/v1/support/portals/{portal_id}/status/",
            {"status": "ARCHIVED"},
            format="json",
        )

        responses = [
            self.client.post(
                f"/api/v1/support/portals/{portal_id}/categories/",
                {"slug": "new", "name": "Новый"},
                format="json",
            ),
            self.client.patch(
                f"/api/v1/support/portals/{portal_id}/categories/{category['id']}/",
                {"name": "Изменён"},
                format="json",
            ),
            self.client.post(
                f"/api/v1/support/portals/{portal_id}/articles/",
                {
                    "categoryId": category["id"],
                    "slug": "draft",
                    "title": "Черновик",
                    "content": "Текст",
                },
                format="json",
            ),
            self.client.put(
                f"/api/v1/support/portals/{portal_id}/products/",
                {"items": []},
                format="json",
            ),
        ]

        self.assertTrue(all(response.status_code == 400 for response in responses))

    def test_category_hierarchy_can_be_updated_and_protected_on_delete(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        parent = self.client.post(
            f"/api/v1/support/portals/{portal_id}/categories/",
            {"slug": "account", "name": "Аккаунт"},
            format="json",
        ).json()["category"]
        child = self.client.post(
            f"/api/v1/support/portals/{portal_id}/categories/",
            {"slug": "security", "name": "Безопасность", "parentId": parent["id"]},
            format="json",
        ).json()["category"]

        updated = self.client.patch(
            f"/api/v1/support/portals/{portal_id}/categories/{child['id']}/",
            {"name": "Защита аккаунта", "parentId": parent["id"], "sortOrder": 4},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(updated.json()["category"]["parentId"], parent["id"])
        protected = self.client.delete(
            f"/api/v1/support/portals/{portal_id}/categories/{parent['id']}/"
        )
        self.assertEqual(protected.status_code, 400, protected.content)

    def test_support_operator_uses_portal_scoped_widget_options(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        widget = create_web_widget(self.channel, name="Foxray support widget")
        response = self.client.get(
            f"/api/v1/support/portals/{portal_id}/support-channels/"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([item["id"] for item in response.json()["items"]], [widget.id])
        self.assertEqual(response.json()["items"][0]["channel"]["id"], self.channel.id)
