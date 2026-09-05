from django.test import TestCase

from chatballs.channels.models import Channel
from chatballs.identity.bootstrap import bootstrap_edevs_owner
from chatballs.products.models import Product
from chatballs.testing import TenantAPIClient


class SupportPortalTestCase(TestCase):
    organization = None
    owner = None
    product = None
    channel = None
    client = None

    def setUp(self) -> None:
        result = bootstrap_edevs_owner(
            email="portal-owner@edevs.tech",
            password="temporary-password",
        )
        self.organization = result.organization
        self.owner = result.owner
        self.product = Product.objects.get(
            organization=self.organization,
            code="foxray",
        )
        self.channel = Channel.objects.create(
            organization=self.organization,
            code="foxray-help",
            name="Foxray support",
            product=self.product,
            requires_authenticated_product_identity=True,
            allow_anonymous_sessions=False,
            allow_self_reported_contact=False,
        )
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.owner)
    def create_portal(self, slug: str = "foxray-help"):
        return self.client.post(
            "/api/v1/support/portals/",
            {"slug": slug, "name": "Foxray Help", "defaultLocale": "ru"},
            format="json",
        )
