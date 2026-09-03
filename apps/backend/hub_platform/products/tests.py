import json

from django.test import TestCase
from hub_platform.testing import TenantAPIClient as APIClient

from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import Department, Organization
from hub_platform.products.models import Product, ProductDepartment, ProductStatus


class ProductApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.sales = Department.objects.get(organization=self.organization, code="sales")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_create_product_is_active_and_assigned_to_department(self) -> None:
        response = self.client.post(
            "/api/v1/company/products/create/",
            data=json.dumps(
                {
                    "code": "academy",
                    "name": "Academy",
                    "siteUrl": "https://academy.edevs.tech",
                    "departmentIds": [self.sales.id],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["product"]
        self.assertEqual(payload["status"], ProductStatus.ACTIVE)
        self.assertEqual(payload["departments"][0]["code"], "sales")
        self.assertTrue(ProductDepartment.objects.filter(product_id=payload["id"], department=self.sales).exists())

    def test_update_does_not_change_product_code(self) -> None:
        product = Product.objects.get(code="firepage")
        response = self.client.patch(
            f"/api/v1/company/products/{product.id}/update/",
            data=json.dumps(
                {
                    "code": "changed-code",
                    "name": "FirePage Updated",
                    "departmentIds": [self.sales.id],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.code, "firepage")
        self.assertEqual(product.name, "FirePage Updated")

    def test_product_detail_is_limited_to_user_organization(self) -> None:
        other = Organization.objects.create(name="Other", slug="other")
        product = Product.objects.create(organization=other, code="other-product", name="Other Product")

        response = self.client.get(f"/api/v1/company/products/{product.id}/")

        self.assertEqual(response.status_code, 404)

    def test_product_payload_exposes_assigned_channels(self) -> None:
        from hub_platform.channels.models import Channel

        product = Product.objects.get(code="firepage")
        Channel.objects.create(organization=self.organization, code="site", name="Сайт", product=product)

        response = self.client.get("/api/v1/company/products/")

        payload = next(item for item in response.json()["items"] if item["id"] == product.id)
        channel = payload["channels"][0]
        self.assertEqual(channel["code"], "site")
        self.assertTrue(channel["isActive"])
        # Единый источник: payload содержит связи, нужные табу каналов продукта.
        self.assertIsNone(channel["agentId"])
        self.assertEqual(channel["connections"], [])
