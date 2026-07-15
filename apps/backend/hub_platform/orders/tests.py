import json

from django.test import TestCase
from django.utils import timezone
from hub_platform.testing import TenantAPIClient as APIClient, system_tenant_context

from hub_platform.conversations.models import Contact
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import Organization
from hub_platform.orders.models import Order, PaymentStatus
from hub_platform.orders.services import OrderItemInput, create_order, mark_paid
from hub_platform.products.models import BillingPeriod, Offer, OfferFulfillmentType, OfferPaymentType, Price, Product


class OrdersTestBase(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.context = system_tenant_context(self.organization)
        self.contact = Contact.objects.create(organization=self.organization, name="Тестовый клиент")
        product = Product.objects.get(code="firepage")
        self.offer = Offer.objects.create(
            product=product, code="box", name="Коробка",
            fulfillment_type=OfferFulfillmentType.BOX_LICENSE, payment_type=OfferPaymentType.ONE_TIME,
        )
        self.price = Price.objects.create(
            offer=self.offer, version=1, amount_minor=490_000, billing_period=BillingPeriod.ONE_TIME, valid_from=timezone.now(),
        )
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")


class OrderServiceTests(OrdersTestBase):
    def test_create_order_uses_active_price(self) -> None:
        order = create_order(context=self.context, contact=self.contact, items=[OrderItemInput(offer_id=self.offer.id)])
        self.assertEqual(order.amount_minor, 490_000)
        self.assertEqual(order.payment_status, PaymentStatus.PENDING)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.product_id, self.offer.product_id)

    def test_mark_paid_sets_paid_at_and_fulfillment(self) -> None:
        order = create_order(context=self.context, contact=self.contact, items=[OrderItemInput(offer_id=self.offer.id)])
        mark_paid(context=self.context, order=order)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, PaymentStatus.PAID)
        self.assertIsNotNone(order.paid_at)


class OrderApiTests(OrdersTestBase):
    def test_create_and_mark_paid_via_api(self) -> None:
        create = self.client.post(
            "/api/v1/orders/",
            data=json.dumps({"contactId": self.contact.id, "items": [{"offerId": self.offer.id}]}),
            content_type="application/json",
        )
        self.assertEqual(create.status_code, 201)
        order_id = create.json()["order"]["id"]

        paid = self.client.post(f"/api/v1/orders/{order_id}/mark-paid/")
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(paid.json()["order"]["paymentStatus"], PaymentStatus.PAID)

    def test_list_filters_by_payment_status(self) -> None:
        order = create_order(context=self.context, contact=self.contact, items=[OrderItemInput(offer_id=self.offer.id)])
        mark_paid(context=self.context, order=order)
        create_order(context=self.context, contact=self.contact, items=[OrderItemInput(offer_id=self.offer.id)])

        response = self.client.get("/api/v1/orders/?paymentStatus=PAID")
        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["paymentStatus"], PaymentStatus.PAID)

    def test_paid_order_reflected_in_sales_stats(self) -> None:
        from hub_platform.conversations.stats import sales_overview_stats

        order = create_order(context=self.context, contact=self.contact, items=[OrderItemInput(offer_id=self.offer.id)])
        mark_paid(context=self.context, order=order)
        stats = sales_overview_stats(self.context, "d30")["period"]
        self.assertEqual(stats["sales"], 1)
        self.assertEqual(stats["revenueMinor"], 490_000)

    def test_order_scoped_to_organization(self) -> None:
        other = Organization.objects.create(name="Other", slug="other")
        other_contact = Contact.objects.create(organization=other, name="Чужой")
        order = Order.objects.create(organization=other, contact=other_contact, amount_minor=100)

        response = self.client.get(f"/api/v1/orders/{order.id}/")
        self.assertEqual(response.status_code, 404)


class OrderIngestTests(OrdersTestBase):
    def setUp(self) -> None:
        super().setUp()
        from hub_platform.orders.services import hash_ingest_token

        self.token = "secret-product-token"
        product = Product.objects.get(code="firepage")
        product.ingest_token_hash = hash_ingest_token(self.token)
        product.save(update_fields=["ingest_token_hash"])
        # Вебхук без сессии.
        self.webhook = APIClient()

    def _post(self, body: dict, token: str | None = "secret-product-token"):
        headers = {"HTTP_X_PRODUCT_TOKEN": token} if token is not None else {}
        return self.webhook.post("/api/v1/orders/ingest/", data=json.dumps(body), content_type="application/json", **headers)

    def test_ingest_creates_paid_order(self) -> None:
        response = self._post({"externalId": "fp-1001", "paymentStatus": "PAID", "contactName": "Гость", "items": [{"offerCode": "box"}]})
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(source="firepage", external_id="fp-1001")
        self.assertEqual(order.payment_status, PaymentStatus.PAID)
        self.assertEqual(order.amount_minor, 490_000)
        self.assertIsNotNone(order.paid_at)

    def test_ingest_is_idempotent(self) -> None:
        first = self._post({"externalId": "fp-1002", "paymentStatus": "PAID", "items": [{"offerCode": "box"}]})
        second = self._post({"externalId": "fp-1002", "paymentStatus": "PAID", "items": [{"offerCode": "box"}]})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Order.objects.filter(external_id="fp-1002").count(), 1)

    def test_ingest_rejects_bad_token(self) -> None:
        response = self._post({"externalId": "x", "items": [{"offerCode": "box"}]}, token="nope")
        self.assertEqual(response.status_code, 401)

    def test_ingest_requires_token(self) -> None:
        response = self._post({"externalId": "x", "items": [{"offerCode": "box"}]}, token=None)
        self.assertEqual(response.status_code, 401)
