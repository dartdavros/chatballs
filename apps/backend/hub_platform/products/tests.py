import json
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.utils import timezone

from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import Department, Organization
from hub_platform.products.models import (
    BillingPeriod,
    Offer,
    OfferFulfillmentType,
    OfferPaymentType,
    Price,
    Product,
    ProductDepartment,
    ProductStatus,
)


class ProductApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.sales = Department.objects.get(organization=self.organization, code="sales")
        self.client = Client()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_create_product_is_active_and_assigned_to_department(self) -> None:
        response = self.client.post(
            "/api/v1/company/products/create/",
            data=json.dumps(
                {
                    "code": "academy",
                    "name": "Academy",
                    "siteUrl": "https://academy.edevs.tech",
                    "summary": "Обучающий продукт",
                    "salesDescription": "Описание для продаж",
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


class ProductCatalogModelTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Edevs", slug="edevs")
        self.product = Product.objects.create(organization=self.organization, code="foxray", name="Foxray")

    def _offer(self, code: str, name: str) -> Offer:
        return Offer.objects.create(
            product=self.product,
            code=code,
            name=name,
            fulfillment_type=OfferFulfillmentType.SAAS_ACCESS,
            payment_type=OfferPaymentType.SUBSCRIPTION,
            fiscal_name=name,
        )

    def test_product_supports_multiple_tariffs_and_period_prices(self) -> None:
        pro = self._offer("pro", "Pro")
        maximum = self._offer("max", "Max")
        now = timezone.now()
        Price.objects.create(
            offer=pro,
            version=1,
            amount_minor=490_000,
            billing_period=BillingPeriod.MONTH,
            valid_from=now,
        )
        Price.objects.create(
            offer=pro,
            version=1,
            amount_minor=4_704_000,
            billing_period=BillingPeriod.YEAR,
            valid_from=now,
        )

        self.assertEqual(self.product.offers.count(), 2)
        self.assertEqual(pro.prices.filter(is_active=True).count(), 2)
        self.assertEqual(maximum.name, "Max")

    def test_only_one_active_price_per_currency_and_period(self) -> None:
        offer = self._offer("pro", "Pro")
        Price.objects.create(
            offer=offer,
            version=1,
            amount_minor=490_000,
            billing_period=BillingPeriod.MONTH,
            valid_from=timezone.now(),
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Price.objects.create(
                offer=offer,
                version=2,
                amount_minor=590_000,
                billing_period=BillingPeriod.MONTH,
                valid_from=timezone.now(),
            )

    def test_support_extension_requires_box_offer(self) -> None:
        support = Offer(
            product=self.product,
            code="support",
            name="Поддержка",
            fulfillment_type=OfferFulfillmentType.SUPPORT_EXTENSION,
            payment_type=OfferPaymentType.ONE_TIME,
            fiscal_name="Продление поддержки",
        )

        with self.assertRaises(ValidationError):
            support.full_clean()

    def test_price_commercial_data_is_immutable(self) -> None:
        offer = self._offer("pro", "Pro")
        price = Price.objects.create(
            offer=offer,
            version=1,
            amount_minor=490_000,
            billing_period=BillingPeriod.MONTH,
            valid_from=timezone.now() - timedelta(days=1),
        )
        price.amount_minor = 590_000

        with self.assertRaises(ValidationError):
            price.save()
