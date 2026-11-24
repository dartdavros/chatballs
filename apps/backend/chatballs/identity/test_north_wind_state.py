from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.utils import timezone

from chatballs.conversations.domain_event_test_base import DomainEventTestBase
from chatballs.conversations.transports import send_reply
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.north_wind.appointments import MOSCOW, book_fitting, fitting_slots
from chatballs.identity.demo_seed.north_wind.local_access import issue_local_read_token
from chatballs.identity.demo_seed.north_wind.orders import find_order, place_order, quote_order
from chatballs.identity.demo_seed.north_wind.state import (
    ShopError,
    execute_write,
    initial_state,
    read_state,
)
from chatballs.integrations.checking import test_integration as check_integration
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.testing import TenantAPIClient


class NorthWindStateTests(DomainEventTestBase):
    def test_checkout_reservation_and_booking_are_bound_to_the_generation(self):
        context = TenantContext.for_resource(self.organization)
        with tenant_atomic(context):
            dataset = DemoDataset.objects.create(
                organization=self.organization,
                status=DemoDatasetStatus.INSTALLED,
                generation=uuid4(),
                shop_state=initial_state(),
            )
        generation = dataset.generation
        purchase = {"customer": "andrey", "product_id": "alpine", "size": "L", "bonus": 750}
        public_quote = quote_order(read_state(context, generation), **{**purchase, "customer": "maria", "bonus": 0})
        self.assertEqual(public_quote["total"], 29900)
        self.assertEqual(public_quote["maxBonus"], 0)
        quote = quote_order(read_state(context, generation), **purchase)
        self.assertEqual(quote["personalPrice"], 26910)
        self.assertEqual(quote["bonusBalance"], 1500)
        self.assertEqual(quote["total"], 26160)
        command = {**purchase, "store": "center", "confirmed": True, "revision": quote["revision"]}
        first = execute_write(context, generation, place_order, key="checkout", command=command)
        self.assertEqual(first["number"], 2042)
        self.assertEqual(first["balanceAfter"], 750)
        self.assertEqual(first["stockAfter"], 2)
        self.assertEqual(
            execute_write(context, generation, place_order, key="checkout", command=command), first,
        )
        with self.assertRaisesRegex(ShopError, "idempotency_conflict"):
            execute_write(context, generation, place_order, key="checkout", command={**command, "store": "gorki"})

        day = timezone.now().astimezone(MOSCOW).date() + timedelta(days=1)
        slot = fitting_slots(read_state(context, generation), store="center", day=day)[0]
        fitting = {
            "customer": "olga", "store": "center", "starts_at": slot,
            "products": ["alpine", "ridge"], "confirmed": True,
        }
        execute_write(context, generation, book_fitting, key="fitting", command=fitting)
        with self.assertRaisesRegex(ShopError, "fitting_slot_unavailable"):
            execute_write(context, generation, book_fitting, key="fitting-again", command=fitting)

        with tenant_atomic(context):
            DemoDataset.objects.filter(pk=dataset.pk).update(generation=uuid4(), shop_state=initial_state())
            dataset.refresh_from_db()
        with self.assertRaisesRegex(ShopError, "demo_generation_unavailable"):
            execute_write(context, generation, place_order, key="checkout", command=command)
        new_state = read_state(context, dataset.generation)
        self.assertEqual(new_state["balances"]["andrey"], 1500)
        self.assertEqual(new_state["stock"]["alpine:L:center"], 3)
        self.assertIn(slot, fitting_slots(new_state, store="center", day=day))
        with self.assertRaisesRegex(ShopError, "order_unavailable"):
            find_order(new_state, customer="andrey", order_number=2042)
        self.assertEqual(
            find_order(new_state, customer="andrey-after-purchase", order_number=2042)["status"], "collected",
        )

        reader = TenantAPIClient()
        url = "/api/v1/demo-local/shop/order-status/"
        token = issue_local_read_token(dataset, customer="andrey-after-purchase")
        response = reader.post(
            url, {"customer": "andrey", "order_number": 2042}, format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.json()["status"], "collected")
        self.assertEqual(reader.post(url, {"order_number": 2042}, format="json").status_code, 403)
        shipment = reader.post(
            "/api/v1/demo-local/shop/shipment-status/",
            {"customer": "andrey", "order_number": 2042}, format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(shipment.status_code, 200, shipment.data)
        self.assertEqual(shipment.json(), {"number": 2042, "status": "collected"})

    def test_demo_messenger_delivery_is_local_and_cannot_use_an_old_generation(self):
        context = TenantContext.for_resource(self.organization)
        with tenant_atomic(context):
            dataset = DemoDataset.objects.create(
                organization=self.organization, status=DemoDatasetStatus.INSTALLED,
                generation=uuid4(), shop_state=initial_state(),
            )
            integration = self.connection
            integration.provider = "TELEGRAM"
            integration.config = {"demoSeed": True, "demoGeneration": str(dataset.generation)}
            integration.save(update_fields=["provider", "config"])
            with patch("chatballs.conversations.transports._SEND", {}) as remote:
                self.assertEqual(check_integration(context=context, integration=integration).status, "OK")
                self.assertTrue(send_reply(integration, chat_id="demo", user_id="", text="Local result"))
                dataset.refresh_from_db()
                self.assertEqual(dataset.shop_state["channelDeliveries"][0]["text"], "Local result")
                dataset.generation = uuid4()
                dataset.shop_state = initial_state()
                dataset.save(update_fields=["generation", "shop_state"])
                self.assertFalse(send_reply(integration, chat_id="demo", user_id="", text="Stale result"))
                self.assertEqual(check_integration(context=context, integration=integration).status, "ERROR")
                self.assertFalse(remote)
