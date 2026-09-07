from django.test import TestCase

from chatballs.channels.models import Channel
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.testing import TenantAPIClient


class SupportPortalTestCase(TestCase):
    organization = None
    owner = None
    channel = None
    client = None

    def setUp(self) -> None:
        result = bootstrap_owner(
            email="portal-owner@example.com",
            password="temporary-password",
        )
        self.organization = result.organization
        self.owner = result.owner
        self.channel = Channel.objects.create(
            organization=self.organization,
            code="app-help",
            name="Приложение support",
        )
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.owner)
    def create_portal(self, slug: str = "app-help"):
        return self.client.post(
            "/api/v1/support/portals/",
            {"slug": slug, "name": "Приложение Help", "defaultLocale": "ru"},
            format="json",
        )
