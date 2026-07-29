from django.test import TestCase, override_settings
from django.utils import timezone

from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.channels.models import Channel
from hub_platform.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
    IntegrationStatus,
)
from hub_platform.support_portals.models import PortalArticleFeedback, SupportPortal
from hub_platform.testing import TenantAPIClient


class PublicSupportPortalTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_edevs_owner(
            email="public-portal-owner@edevs.tech",
            password="temporary-password",
        )
        self.client = TenantAPIClient()
        self.client.force_authenticate(result.owner)
        portal = self.client.post(
            "/api/v1/support/portals/",
            {"slug": "edevs-help", "name": "Edevs Help"},
            format="json",
        ).json()["portal"]
        self.portal_id = portal["id"]
        self.portal_host = portal["hostedDomain"]
        widget_channel = Channel.objects.create(
            organization=result.organization,
            code="edevs-help-chat",
            name="Edevs Help — чат",
            department=result.support_department,
            requires_authenticated_product_identity=False,
            allow_anonymous_sessions=True,
        )
        Integration.objects.create(
            organization=result.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.WEB,
            name="Edevs Help widget",
            channel=widget_channel,
            status=IntegrationStatus.OK,
        )
        self.client.patch(
            f"/api/v1/support/portals/{self.portal_id}/",
            {"widgetChannelId": widget_channel.id},
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
            bootstrap_edevs_owner(
                email="public-portal-owner@edevs.tech",
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
        self.assertEqual(portal.json()["portal"]["name"], "Edevs Help")
        self.assertEqual(
            portal.json()["portal"]["webWidgetChannelCode"],
            "edevs-help-chat",
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

    @override_settings(ALLOWED_HOSTS=["testserver", "help.foxray.example"])
    def test_verified_custom_domain_resolves_the_same_portal(self) -> None:
        self.client.force_authenticate(
            bootstrap_edevs_owner(
                email="public-portal-owner@edevs.tech",
                password="temporary-password",
            ).owner
        )
        self.client.post(
            f"/api/v1/support/portals/{self.portal_id}/status/",
            {"status": "PUBLISHED"},
            format="json",
        )
        SupportPortal.objects.filter(id=self.portal_id).update(
            custom_domain="help.foxray.example",
            custom_domain_verified_at=timezone.now(),
        )
        self.client.logout()

        response = self.client.get(
            "/api/v1/help/",
            HTTP_HOST="help.foxray.example",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["portal"]["name"], "Edevs Help")

    @override_settings(ROOT_URLCONF="hub_backend.urls_platform")
    def test_gateway_authorizes_only_published_portal_domains(self) -> None:
        custom_domain = "help.foxray.example"
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
