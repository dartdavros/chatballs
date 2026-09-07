from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.channels.models import Channel
from chatballs.support_portals.models import PortalArticleFeedback, SupportPortal
from chatballs.testing import TenantAPIClient
from chatballs.webchat.testing import create_web_widget


class PublicSupportPortalTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_owner(
            email="public-portal-owner@example.com",
            password="temporary-password",
        )
        self.client = TenantAPIClient()
        self.client.force_authenticate(result.owner)
        portal = self.client.post(
            "/api/v1/support/portals/",
            {"slug": "demo-help", "name": "Acme Help"},
            format="json",
        ).json()["portal"]
        self.portal_id = portal["id"]
        self.portal_host = portal["hostedDomain"]
        widget_channel = Channel.objects.create(
            organization=result.organization,
            code="demo-help-chat",
            name="Acme Help — чат",
            requires_authenticated_product_identity=False,
            allow_anonymous_sessions=True,
        )
        self.widget = create_web_widget(widget_channel, name="Acme Help widget")
        self.client.patch(
            f"/api/v1/support/portals/{self.portal_id}/",
            {"widgetId": self.widget.id},
            format="json",
        )
        category = self.client.post(
            f"/api/v1/support/portals/{self.portal_id}/categories/",
            {
                "slug": "getting-started",
                "name": "Начало работы",
                "description": "Быстрый старт и основные возможности",
            },
            format="json",
        ).json()["category"]
        article = self.client.post(
            f"/api/v1/support/portals/{self.portal_id}/articles/",
            {
                "categoryId": category["id"],
                "slug": "first-steps",
                "title": "Первые шаги",
                "summary": "Начало работы с продуктом",
                "content": "# Первые шаги\n\nОткройте кабинет.",
            },
            format="json",
        ).json()["article"]
        self.owner = result.owner
        self.article_id = article["id"]
        revision_id = article["revisions"][0]["id"]
        self.client.post(
            f"/api/v1/support/portals/{self.portal_id}/articles/{article['id']}/publish/",
            {"revisionId": revision_id},
            format="json",
        )
        self.client.logout()

    def test_draft_portal_is_not_public(self) -> None:
        response = self.client.get("/api/v1/help/", HTTP_HOST=self.portal_host)
        self.assertEqual(response.status_code, 404)

    def test_published_portal_exposes_search_article_and_feedback(self) -> None:
        self.client.force_authenticate(
            bootstrap_owner(
                email="public-portal-owner@example.com",
                password="temporary-password",
            ).owner
        )
        published = self.client.post(
            f"/api/v1/support/portals/{self.portal_id}/status/",
            {"status": "PUBLISHED"},
            format="json",
        )
        self.assertEqual(published.status_code, 200, published.content)
        self.client.logout()

        portal = self.client.get("/api/v1/help/", HTTP_HOST=self.portal_host)
        self.assertEqual(portal.status_code, 200, portal.content)
        self.assertEqual(portal.json()["portal"]["name"], "Acme Help")
        self.assertEqual(
            portal.json()["portal"]["webWidgetKey"],
            self.widget.public_key,
        )
        self.assertEqual(
            portal.json()["categories"][0]["description"],
            "Быстрый старт и основные возможности",
        )
        self.assertEqual(portal.json()["categories"][0]["articleCount"], 1)

        search = self.client.get(
            "/api/v1/help/articles/?q=кабинет",
            HTTP_HOST=self.portal_host,
        )
        self.assertEqual(search.status_code, 200, search.content)
        self.assertEqual(len(search.json()["items"]), 1)
        self.assertNotIn("content", search.json()["items"][0]["revision"])
        self.assertEqual(search.json()["pagination"]["total"], 1)

        article = self.client.get(
            "/api/v1/help/articles/first-steps/",
            HTTP_HOST=self.portal_host,
        )
        self.assertEqual(article.status_code, 200, article.content)
        self.assertIn("Откройте кабинет", article.json()["article"]["revision"]["content"])

        feedback = self.client.post(
            "/api/v1/help/articles/first-steps/feedback/",
            {"helpful": True},
            format="json",
            HTTP_HOST=self.portal_host,
        )
        self.assertEqual(feedback.status_code, 201, feedback.content)
        self.assertEqual(PortalArticleFeedback.objects.filter(helpful=True).count(), 1)

    @override_settings(ALLOWED_HOSTS=["testserver", "help.app.example"])
    def test_verified_custom_domain_resolves_the_same_portal(self) -> None:
        self.client.force_authenticate(
            bootstrap_owner(
                email="public-portal-owner@example.com",
                password="temporary-password",
            ).owner
        )
        self.client.post(
            f"/api/v1/support/portals/{self.portal_id}/status/",
            {"status": "PUBLISHED"},
            format="json",
        )
        SupportPortal.objects.filter(id=self.portal_id).update(
            custom_domain="help.app.example",
            custom_domain_verified_at=timezone.now(),
        )
        self.client.logout()

        response = self.client.get(
            "/api/v1/help/",
            HTTP_HOST="help.app.example",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["portal"]["name"], "Acme Help")

    def test_attachments_list_every_file_absent_from_the_text(self) -> None:
        """Картинка, вставленная в статью, видна в тексте; всё остальное —

        вложение под статьёй, независимо от типа файла: посетитель должен
        как-то добраться до прикреплённого PDF и до прикреплённой картинки.
        """
        self.client.force_authenticate(self.owner)
        published = self.client.post(
            f"/api/v1/support/portals/{self.portal_id}/status/",
            {"status": "PUBLISHED"},
            format="json",
        )
        self.assertEqual(published.status_code, 200, published.content)
        article_id = self.article_id
        inserted = self.client.post(
            f"/api/v1/support/portals/{self.portal_id}/articles/{article_id}/files/",
            {"file": SimpleUploadedFile("scheme.png", b"png-bytes", content_type="image/png")},
            format="multipart",
        ).json()["file"]
        attached_image = self.client.post(
            f"/api/v1/support/portals/{self.portal_id}/articles/{article_id}/files/",
            {"file": SimpleUploadedFile("logo.svg", b"<svg/>", content_type="image/svg+xml")},
            format="multipart",
        ).json()["file"]
        attached_doc = self.client.post(
            f"/api/v1/support/portals/{self.portal_id}/articles/{article_id}/files/",
            {"file": SimpleUploadedFile("price.pdf", b"%PDF-", content_type="application/pdf")},
            format="multipart",
        ).json()["file"]
        revision = self.client.post(
            f"/api/v1/support/portals/{self.portal_id}/articles/{article_id}/revisions/",
            {
                "title": "Первые шаги",
                "summary": "Начало работы с продуктом",
                "content": "Схема: ![схема](" + inserted["path"] + ")",
            },
            format="json",
        ).json()["revision"]
        self.client.post(
            f"/api/v1/support/portals/{self.portal_id}/articles/{article_id}/publish/",
            {"revisionId": revision["id"]},
            format="json",
        )
        self.client.logout()

        response = self.client.get(
            "/api/v1/help/articles/first-steps/", HTTP_HOST=self.portal_host
        )
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()["article"]
        self.assertIn(inserted["path"], payload["revision"]["content"])
        self.assertEqual(
            sorted(item["name"] for item in payload["attachments"]),
            sorted([attached_doc["name"], attached_image["name"]]),
        )

    @override_settings(ROOT_URLCONF="chatballs_backend.urls_platform")
    def test_gateway_authorizes_only_published_portal_domains(self) -> None:
        custom_domain = "help.app.example"
        SupportPortal.objects.filter(id=self.portal_id).update(
            status="PUBLISHED",
            custom_domain=custom_domain,
        )

        hosted = self.client.get(
            "/api/v1/gateway/help-domain/",
            {"domain": self.portal_host},
        )
        unverified = self.client.get(
            "/api/v1/gateway/help-domain/",
            {"domain": custom_domain},
        )

        self.assertEqual(hosted.status_code, 204, hosted.content)
        self.assertEqual(unverified.status_code, 404, unverified.content)

        SupportPortal.objects.filter(id=self.portal_id).update(
            custom_domain_verified_at=timezone.now(),
        )
        verified = self.client.get(
            "/api/v1/gateway/help-domain/",
            {"domain": custom_domain},
        )

        self.assertEqual(verified.status_code, 204, verified.content)
