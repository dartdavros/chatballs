from django.core.files.uploadedfile import SimpleUploadedFile

from chatballs.support_portals.tests.base import SupportPortalTestCase
from chatballs.webchat.testing import create_web_widget


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

    def test_article_files_are_uploaded_listed_and_deleted(self) -> None:
        # Файлы статьи — рейка редактора и drop в текст (кадры PT7/PT8).
        portal_id = self.create_portal().json()["portal"]["id"]
        category = self.client.post(
            f"/api/v1/support/portals/{portal_id}/categories/",
            {"name": "Мерки"},
            format="json",
        ).json()["category"]
        article_id = self.client.post(
            f"/api/v1/support/portals/{portal_id}/articles/",
            {
                "categoryId": category["id"],
                "slug": "kak-snyat-merki",
                "title": "Как снять мерки",
                "summary": "",
                "content": "# Как снять мерки",
            },
            format="json",
        ).json()["article"]["id"]

        upload = self.client.post(
            f"/api/v1/support/portals/{portal_id}/articles/{article_id}/files/",
            {
                "file": SimpleUploadedFile(
                    "measure-points.png", b"png-bytes", content_type="image/png"
                )
            },
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201, upload.content)
        uploaded = upload.json()["file"]
        self.assertEqual(uploaded["name"], "measure-points.png")
        self.assertEqual(uploaded["size"], len(b"png-bytes"))
        self.assertIn("/api/v1/help/files/", uploaded["url"])

        detail = self.client.get(
            f"/api/v1/support/portals/{portal_id}/articles/{article_id}/"
        )
        self.assertEqual(detail.status_code, 200, detail.content)
        self.assertEqual(
            [item["name"] for item in detail.json()["article"]["files"]],
            ["measure-points.png"],
        )
        self.assertEqual(detail.json()["article"]["fileCount"], 1)

        removed = self.client.delete(
            f"/api/v1/support/portals/{portal_id}/articles/{article_id}"
            f"/files/{uploaded['id']}/"
        )
        self.assertEqual(removed.status_code, 204, removed.content)
        listing = self.client.get(
            f"/api/v1/support/portals/{portal_id}/articles/{article_id}/files/"
        )
        self.assertEqual(listing.json()["items"], [])

    def test_absolute_file_links_become_relative(self) -> None:
        """CSP портала (img-src 'self') режет картинку с чужим хостом.

        Ссылка на файл статьи всегда относительная: и в новой редакции, и в
        отдаче старых — иначе изображение просто не появляется на портале.
        """
        portal_id = self.create_portal().json()["portal"]["id"]
        category = self.client.post(
            f"/api/v1/support/portals/{portal_id}/categories/",
            {"name": "Доставка"},
            format="json",
        )
        path = "/api/v1/help/files/4ecee829-30d2-4a2a-904e-a09be28d7708/"
        article = self.client.post(
            f"/api/v1/support/portals/{portal_id}/articles/",
            {
                "categoryId": category.json()["category"]["id"],
                "slug": "delivery",
                "title": "Доставка",
                "summary": "Сроки",
                "content": f"![кот](http://localhost{path})",
            },
            format="json",
        )
        self.assertEqual(article.status_code, 201, article.content)
        content = article.json()["article"]["revisions"][0]["content"]
        self.assertEqual(content, f"![кот]({path})")

        article_id = article.json()["article"]["id"]
        revision = self.client.post(
            f"/api/v1/support/portals/{portal_id}/articles/{article_id}/revisions/",
            {
                "title": "Доставка",
                "summary": "Сроки",
                "content": f"![кот](https://help.example.com:8443{path})",
            },
            format="json",
        )
        self.assertEqual(revision.status_code, 201, revision.content)
        self.assertEqual(revision.json()["revision"]["content"], f"![кот]({path})")

    def test_revision_keeps_its_author(self) -> None:
        # Рейка версий показывает автора редакции (кадр PT7).
        portal_id = self.create_portal().json()["portal"]["id"]
        category = self.client.post(
            f"/api/v1/support/portals/{portal_id}/categories/",
            {"name": "Аккаунт"},
            format="json",
        ).json()["category"]
        article_id = self.client.post(
            f"/api/v1/support/portals/{portal_id}/articles/",
            {
                "categoryId": category["id"],
                "slug": "sign-in",
                "title": "Вход",
                "summary": "",
                "content": "Версия 1",
            },
            format="json",
        ).json()["article"]["id"]
        revision = self.client.post(
            f"/api/v1/support/portals/{portal_id}/articles/{article_id}/revisions/",
            {"title": "Вход", "summary": "", "content": "Версия 2"},
            format="json",
        )
        self.assertEqual(revision.status_code, 201, revision.content)
        self.assertTrue(revision.json()["revision"]["authorName"])

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
        widget = create_web_widget(self.channel, name="Приложение support widget")
        response = self.client.get(f"/api/v1/support/portals/{portal_id}/widgets/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([item["id"] for item in response.json()["items"]], [widget.id])
        self.assertEqual(response.json()["items"][0]["channel"]["id"], self.channel.id)


class ArticleFileServingTests(SupportPortalTestCase):
    """Отдача файлов статьи посетителю портала.

    Тип содержимого приходит от загружающего, а страница открывается на домене
    портала: inline пускаем только картинки и PDF, остальное — скачиванием.
    """

    def setUp(self) -> None:
        super().setUp()
        portal_id = self.create_portal().json()["portal"]["id"]
        category = self.client.post(
            f"/api/v1/support/portals/{portal_id}/categories/",
            {"name": "Раздел"},
            format="json",
        ).json()["category"]
        article_id = self.client.post(
            f"/api/v1/support/portals/{portal_id}/articles/",
            {
                "categoryId": category["id"],
                "slug": "statya",
                "title": "Статья",
                "summary": "",
                "content": "# Статья",
            },
            format="json",
        ).json()["article"]["id"]
        self.files_url = f"/api/v1/support/portals/{portal_id}/articles/{article_id}/files/"

    def _upload(self, name: str, content_type: str) -> dict:
        response = self.client.post(
            self.files_url,
            {"file": SimpleUploadedFile(name, b"bytes", content_type=content_type)},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["file"]

    def test_image_is_served_inline_for_the_img_tag(self) -> None:
        uploaded = self._upload("shema.png", "image/png")

        served = self.client.get(uploaded["path"])

        self.assertEqual(served.status_code, 200)
        self.assertEqual(served.headers["Content-Type"], "image/png")
        self.assertNotIn("attachment", served.headers.get("Content-Disposition", ""))
        self.assertIn("default-src 'none'", served.headers["Content-Security-Policy"])

    def test_html_disguised_as_upload_is_not_rendered_on_the_portal_domain(self) -> None:
        uploaded = self._upload("payload.html", "text/html")

        served = self.client.get(uploaded["path"])

        self.assertEqual(served.status_code, 200)
        self.assertIn("attachment", served.headers["Content-Disposition"])
        self.assertIn("default-src 'none'", served.headers["Content-Security-Policy"])

    def test_content_type_from_the_client_is_not_taken_as_is(self) -> None:
        # image/png с параметрами и произвольная строка приводятся к типу,
        # который мы готовы поставить в заголовок ответа.
        with_parameters = self._upload("shema.png", "image/png; charset=utf-8")
        self.assertEqual(with_parameters["contentType"], "image/png")

        forged = self._upload("dogovor.pdf", "не тип вовсе")
        self.assertEqual(forged["contentType"], "application/pdf")
