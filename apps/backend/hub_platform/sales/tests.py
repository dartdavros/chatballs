import json

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from hub_platform.conversations.models import Contact, Conversation
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import Organization
from hub_platform.products.models import Product
from hub_platform.sales.models import (
    AttributionMethod,
    Environment,
    ExternalCustomerIdentity,
    Sale,
    SaleEvent,
    SalesSource,
    SalesSourceStatus,
    SaleStatus,
    SourceType,
)
from hub_platform.sales.services import (
    hash_credential,
    issue_attribution_token,
    issue_sales_source_credential,
)


class SalesTestBase(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.product = Product.objects.get(code="firepage")
        self.source = SalesSource.objects.create(
            organization=self.organization, product=self.product, code="product-api", environment=Environment.PRODUCTION
        )
        self.key = issue_sales_source_credential(source=self.source)
        self.api = APIClient()  # Product Sales API — без сессии

    def _post_event(self, body: dict, key: str | None = None):
        headers = {}
        token = self.key if key is None else key
        if token is not None:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return self.api.post("/api/v1/product-sales/events", data=json.dumps(body), content_type="application/json", **headers)

    def _confirmed(self, external_sale_id="order-1", event_id="evt-1", amount=79000, **sale_extra) -> dict:
        sale = {"external_sale_id": external_sale_id, "amount_minor": amount, "currency": "RUB"}
        sale.update(sale_extra)
        return {
            "schema_version": 1,
            "event_id": event_id,
            "event_type": "sale.confirmed",
            "occurred_at": "2026-07-11T18:20:00Z",
            "sale": sale,
        }


class ProductSalesApiTests(SalesTestBase):
    def test_confirmed_creates_sale(self) -> None:
        response = self._post_event(self._confirmed())
        self.assertEqual(response.status_code, 202)
        self.assertFalse(response.json()["duplicate"])
        sale = Sale.objects.get(sales_source=self.source, external_sale_id="order-1")
        self.assertEqual(sale.amount_minor, 79000)
        self.assertEqual(sale.status, SaleStatus.CONFIRMED)
        self.assertEqual(sale.environment, Environment.PRODUCTION)
        self.assertEqual(sale.events.count(), 1)

    def test_duplicate_event_is_idempotent(self) -> None:
        first = self._post_event(self._confirmed(event_id="evt-dup"))
        second = self._post_event(self._confirmed(event_id="evt-dup"))
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["duplicate"])
        self.assertEqual(Sale.objects.filter(external_sale_id="order-1").count(), 1)
        self.assertEqual(SaleEvent.objects.filter(external_event_id="evt-dup").count(), 1)

    def test_new_event_on_existing_sale_is_journalled(self) -> None:
        self._post_event(self._confirmed(event_id="evt-a"))
        second = self._post_event(self._confirmed(event_id="evt-b"))
        self.assertEqual(second.status_code, 202)
        sale = Sale.objects.get(external_sale_id="order-1")
        self.assertEqual(sale.events.count(), 2)

    def test_partial_refund_updates_projection(self) -> None:
        self._post_event(self._confirmed(event_id="evt-1"))
        refund = {
            "schema_version": 1,
            "event_id": "evt-refund",
            "event_type": "sale.partially_refunded",
            "occurred_at": "2026-07-15T10:00:00Z",
            "sale": {"external_sale_id": "order-1", "amount_minor": 79000, "refunded_amount_minor": 20000, "currency": "RUB"},
        }
        response = self._post_event(refund)
        self.assertEqual(response.status_code, 202)
        sale = Sale.objects.get(external_sale_id="order-1")
        self.assertEqual(sale.refunded_amount_minor, 20000)
        self.assertEqual(sale.net_amount_minor, 59000)
        self.assertEqual(sale.status, SaleStatus.PARTIALLY_REFUNDED)

    def test_full_refund_zeroes_net(self) -> None:
        self._post_event(self._confirmed(event_id="evt-1"))
        refund = {
            "schema_version": 1,
            "event_id": "evt-refund-full",
            "event_type": "sale.refunded",
            "occurred_at": "2026-07-16T10:00:00Z",
            "sale": {"external_sale_id": "order-1", "amount_minor": 79000, "currency": "RUB"},
        }
        self._post_event(refund)
        sale = Sale.objects.get(external_sale_id="order-1")
        self.assertEqual(sale.status, SaleStatus.REFUNDED)
        self.assertEqual(sale.net_amount_minor, 0)

    def test_cancel_excludes_from_revenue(self) -> None:
        self._post_event(self._confirmed(event_id="evt-1"))
        cancel = {
            "schema_version": 1,
            "event_id": "evt-cancel",
            "event_type": "sale.cancelled",
            "occurred_at": "2026-07-17T10:00:00Z",
            "sale": {"external_sale_id": "order-1", "amount_minor": 79000, "currency": "RUB"},
        }
        self._post_event(cancel)
        sale = Sale.objects.get(external_sale_id="order-1")
        self.assertEqual(sale.status, SaleStatus.CANCELLED)

    def test_invalid_credential_rejected(self) -> None:
        response = self._post_event(self._confirmed(), key="nope")
        self.assertEqual(response.status_code, 401)

    def test_disabled_source_rejected(self) -> None:
        self.source.status = SalesSourceStatus.DISABLED
        self.source.save(update_fields=["status"])
        response = self._post_event(self._confirmed())
        self.assertEqual(response.status_code, 401)

    def test_unsupported_event_type(self) -> None:
        body = self._confirmed()
        body["event_type"] = "sale.exploded"
        response = self._post_event(body)
        self.assertEqual(response.status_code, 422)

    def test_missing_required_field(self) -> None:
        body = self._confirmed()
        del body["sale"]["amount_minor"]
        response = self._post_event(body)
        self.assertEqual(response.status_code, 400)

    def test_reused_event_id_conflict(self) -> None:
        self._post_event(self._confirmed(event_id="evt-x", external_sale_id="order-1"))
        body = self._confirmed(event_id="evt-x", external_sale_id="order-1")
        body["event_type"] = "sale.refunded"
        response = self._post_event(body)
        self.assertEqual(response.status_code, 409)


class AttributionTests(SalesTestBase):
    def setUp(self) -> None:
        super().setUp()
        from hub_platform.channels.models import Channel

        self.contact = Contact.objects.create(organization=self.organization, name="Клиент")
        channel = Channel.objects.filter(organization=self.organization).first()
        if channel is None:
            channel = Channel.objects.create(organization=self.organization, code="web", name="Web")
        self.conversation = Conversation.objects.create(organization=self.organization, channel=channel, contact=self.contact)

    def test_valid_token_attributes_sale(self) -> None:
        token, raw = issue_attribution_token(
            organization=self.organization,
            product=self.product,
            contact=self.contact,
            conversation=self.conversation,
            actor_type="OWNER",
            actor_id="1",
        )
        body = self._confirmed(external_customer_id="cust-1")
        body["attribution_token"] = raw
        self._post_event(body)
        sale = Sale.objects.get(external_sale_id="order-1")
        self.assertEqual(sale.attribution_method, AttributionMethod.ATTRIBUTION_TOKEN)
        self.assertEqual(sale.contact_id, self.contact.id)
        self.assertEqual(sale.conversation_id, self.conversation.id)
        # Identity создаётся для повторных продаж.
        self.assertTrue(
            ExternalCustomerIdentity.objects.filter(product=self.product, external_customer_id="cust-1").exists()
        )

    def test_repeat_sale_uses_identity_without_inheriting_actor(self) -> None:
        ExternalCustomerIdentity.objects.create(
            organization=self.organization,
            product=self.product,
            environment=Environment.PRODUCTION,
            external_customer_id="cust-2",
            contact=self.contact,
        )
        body = self._confirmed(external_sale_id="order-2", external_customer_id="cust-2")
        self._post_event(body)
        sale = Sale.objects.get(external_sale_id="order-2")
        self.assertEqual(sale.attribution_method, AttributionMethod.EXTERNAL_IDENTITY)
        self.assertEqual(sale.contact_id, self.contact.id)
        self.assertEqual(sale.attributed_actor_type, "")

    def test_unknown_token_still_saves_sale_unattributed(self) -> None:
        body = self._confirmed()
        body["attribution_token"] = "totally-unknown"
        response = self._post_event(body)
        self.assertEqual(response.status_code, 202)
        sale = Sale.objects.get(external_sale_id="order-1")
        self.assertEqual(sale.attribution_method, AttributionMethod.NONE)


class ManualSaleTests(SalesTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.contact = Contact.objects.create(organization=self.organization, name="Клиент")
        self.session = APIClient()
        self.session.login(username="owner@edevs.tech", password="temporary-password")

    def test_manual_create_via_api(self) -> None:
        response = self.session.post(
            "/api/v1/sales/",
            data=json.dumps(
                {
                    "productCode": "firepage",
                    "contactId": self.contact.id,
                    "amountMinor": 490000,
                    "currency": "RUB",
                    "reason": "оплата по счёту",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        sale_id = response.json()["sale"]["id"]
        sale = Sale.objects.get(id=sale_id)
        self.assertEqual(sale.source_type, SourceType.MANUAL)
        self.assertEqual(sale.amount_minor, 490000)
        self.assertTrue(sale.external_sale_id.startswith("manual-"))
        self.assertEqual(sale.events.count(), 1)

    def test_manual_refund_action_appends_event(self) -> None:
        create = self.session.post(
            "/api/v1/sales/",
            data=json.dumps({"productCode": "firepage", "contactId": self.contact.id, "amountMinor": 490000, "currency": "RUB", "reason": "x"}),
            content_type="application/json",
        )
        sale_id = create.json()["sale"]["id"]
        refund = self.session.post(
            f"/api/v1/sales/{sale_id}/partial-refund/",
            data=json.dumps({"refundedAmountMinor": 100000, "reason": "частичный возврат"}),
            content_type="application/json",
        )
        self.assertEqual(refund.status_code, 200)
        sale = Sale.objects.get(id=sale_id)
        self.assertEqual(sale.refunded_amount_minor, 100000)
        self.assertEqual(sale.status, SaleStatus.PARTIALLY_REFUNDED)
        self.assertEqual(sale.events.count(), 2)

    def test_sale_scoped_to_organization(self) -> None:
        other = Organization.objects.create(name="Other", slug="other")
        other_product = Product.objects.create(organization=other, code="p2", name="P2")
        other_source = SalesSource.objects.create(organization=other, product=other_product, code="product-api")
        sale = Sale.objects.create(
            organization=other, product=other_product, sales_source=other_source, source_type=SourceType.PRODUCT_API,
            external_sale_id="x", amount_minor=100, currency="RUB", occurred_at=timezone.now(),
        )
        response = self.session.get(f"/api/v1/sales/{sale.id}/")
        self.assertEqual(response.status_code, 404)


class AnalyticsTests(SalesTestBase):
    def test_analytics_counts_net_revenue(self) -> None:
        self._post_event(self._confirmed(event_id="e1", external_sale_id="o1", amount=100000))
        self._post_event(
            {
                "schema_version": 1,
                "event_id": "e2",
                "event_type": "sale.partially_refunded",
                "occurred_at": "2026-07-12T10:00:00Z",
                "sale": {"external_sale_id": "o1", "amount_minor": 100000, "refunded_amount_minor": 40000, "currency": "RUB"},
            }
        )
        from hub_platform.sales.analytics import sales_analytics

        data = sales_analytics(self.organization.id)
        self.assertEqual(data["grossSalesCount"], 1)
        self.assertEqual(data["grossRevenueMinor"], 100000)
        self.assertEqual(data["refundedAmountMinor"], 40000)
        self.assertEqual(data["netRevenueMinor"], 60000)


class CredentialHashTests(TestCase):
    def test_hash_is_stable(self) -> None:
        self.assertEqual(hash_credential("abc"), hash_credential("abc"))
        self.assertNotEqual(hash_credential("abc"), hash_credential("abd"))


class LegacyMigrationTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.product = Product.objects.get(code="firepage")
        self.contact = Contact.objects.create(organization=self.organization, name="Клиент")

    def _order(self, *, payment_status: str, source: str = "", external_id: str = "", amount: int = 490000):
        from hub_platform.orders.models import Order

        return Order.objects.create(
            organization=self.organization,
            contact=self.contact,
            product=self.product,
            payment_status=payment_status,
            fulfillment_status="DELIVERED" if payment_status == "PAID" else "NONE",
            amount_minor=amount,
            currency="RUB",
            source=source,
            external_id=external_id,
        )

    def test_classification(self) -> None:
        from hub_platform.sales.services import (
            LEGACY_CLASS_EXTERNAL,
            LEGACY_CLASS_MANUAL,
            LEGACY_CLASS_PENDING,
            classify_legacy_order,
        )

        external = self._order(payment_status="PAID", source="firepage", external_id="fp-1")
        manual = self._order(payment_status="PAID")
        pending = self._order(payment_status="PENDING")
        self.assertEqual(classify_legacy_order(external), LEGACY_CLASS_EXTERNAL)
        self.assertEqual(classify_legacy_order(manual), LEGACY_CLASS_MANUAL)
        self.assertEqual(classify_legacy_order(pending), LEGACY_CLASS_PENDING)

    def test_import_creates_legacy_sale_idempotently(self) -> None:
        from hub_platform.sales.services import import_legacy_order

        order = self._order(payment_status="PAID", source="firepage", external_id="fp-100")
        sale, created = import_legacy_order(order=order)
        again, created_again = import_legacy_order(order=order)
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(sale.id, again.id)
        self.assertEqual(sale.source_type, SourceType.LEGACY_IMPORT)
        self.assertEqual(sale.status, SaleStatus.CONFIRMED)
        self.assertIsNone(sale.sales_source_id)
        self.assertEqual(sale.external_sale_id, "fp-100")
        self.assertEqual(sale.metadata["legacy_order_id"], order.id)
        self.assertEqual(sale.metadata["legacy_fulfillment_status"], "DELIVERED")
        self.assertEqual(sale.events.count(), 1)
        self.assertEqual(sale.events.first().event_type, "sale.legacy_imported")

    def test_refunded_order_maps_to_zero_net(self) -> None:
        from hub_platform.sales.services import import_legacy_order

        order = self._order(payment_status="REFUNDED", amount=200000)
        sale, _ = import_legacy_order(order=order)
        self.assertEqual(sale.status, SaleStatus.REFUNDED)
        self.assertEqual(sale.refunded_amount_minor, 200000)
        self.assertEqual(sale.net_amount_minor, 0)
        self.assertTrue(sale.external_sale_id.startswith("legacy-"))

    def test_pending_order_is_not_a_sale(self) -> None:
        from hub_platform.sales.services import SalesApiError, import_legacy_order

        order = self._order(payment_status="PENDING")
        with self.assertRaises(SalesApiError):
            import_legacy_order(order=order)

    def test_dry_run_writes_nothing(self) -> None:
        from django.core.management import call_command

        self._order(payment_status="PAID", source="firepage", external_id="fp-dry")
        call_command("import_legacy_orders")
        self.assertEqual(Sale.objects.count(), 0)

    def test_apply_imports_and_skips_pending(self) -> None:
        from django.core.management import call_command

        self._order(payment_status="PAID", source="firepage", external_id="fp-a")
        self._order(payment_status="CANCELLED")
        self._order(payment_status="PENDING")
        call_command("import_legacy_orders", "--apply")
        self.assertEqual(Sale.objects.count(), 2)
        self.assertEqual(Sale.objects.filter(status=SaleStatus.CANCELLED).count(), 1)

    def test_provision_copies_ingest_token_hash(self) -> None:
        from hub_platform.sales.services import provision_product_sales_source

        self.product.ingest_token_hash = "a" * 64
        self.product.save(update_fields=["ingest_token_hash"])
        source, created, copied = provision_product_sales_source(product=self.product)
        self.assertTrue(created)
        self.assertTrue(copied)
        self.assertEqual(source.credential_hash, "a" * 64)
