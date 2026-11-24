from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase
from django.utils import timezone

from chatballs.conversations.domain_event_test_base import DomainEventTestBase
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.north_wind.after_sales import (
    exchange_options,
    refund_payment,
    request_exchange,
)
from chatballs.identity.demo_seed.north_wind.delivery import (
    delivery_check_result,
    request_delivery_check,
)
from chatballs.identity.demo_seed.north_wind.loyalty_cases import select_loyalty_case
from chatballs.identity.demo_seed.north_wind.orders import place_order, quote_order
from chatballs.identity.demo_seed.north_wind.proposal_document import proposal_path
from chatballs.identity.demo_seed.north_wind.state import ShopError, initial_state
from chatballs.identity.demo_seed.north_wind.wholesale import (
    create_proposal,
    party_options,
    prepare_party_quote,
)
from chatballs.tenancy.database import tenant_atomic
from chatballs.testing import TenantAPIClient


class NorthWindSalesTests(SimpleTestCase):
    def test_loyalty_branches_invalidate_a_quote_before_checkout(self):
        state = initial_state()
        fields = {"customer": "andrey", "product_id": "alpine", "size": "L"}
        quote = quote_order(state, **fields, bonus=750)
        original_stock = dict(state["stock"])
        checkout = {**fields, "bonus": 750, "store": "gorki", "confirmed": True, "revision": quote["revision"]}

        updated = select_loyalty_case(state, case="price-plus-2000")
        self.assertEqual(updated["personalPrice"], 28710)
        with self.assertRaisesRegex(ShopError, "quote_changed"):
            place_order(state, **checkout)
        updated = select_loyalty_case(state, case="balance-600")
        self.assertEqual(updated["maxBonus"], 600)
        with self.assertRaisesRegex(ShopError, "bonus_limit"):
            place_order(state, **checkout)
        updated = select_loyalty_case(state, case="excluded")
        self.assertFalse(updated["bonusesAllowed"])
        self.assertEqual(updated["maxBonus"], 0)
        with self.assertRaisesRegex(ShopError, "bonuses_unavailable"):
            place_order(state, **checkout)
        self.assertFalse(state["orders"])
        self.assertEqual(state["stock"], original_stock)
        self.assertEqual(state["balances"]["andrey"], 1500)

    def test_carrier_check_keeps_the_outcome_pending_until_its_reply(self):
        state = initial_state()
        arguments = {"customer": "pavel", "order_number": 2043, "reference": str(uuid4())}
        self.assertEqual(request_delivery_check(state, **arguments, confirmed=True), {"pending": True})
        self.assertEqual(delivery_check_result(state, **arguments), {"pending": True})
        with patch("chatballs.identity.demo_seed.north_wind.delivery.timezone.now",
                   return_value=timezone.now() + timedelta(seconds=4)):
            reply = delivery_check_result(state, **arguments)
        self.assertEqual(reply["number"], 2043)
        self.assertIs(reply["confirmedEta"], False)

    def test_exchange_checks_identity_duration_alternative_stock_and_confirmation(self):
        state = initial_state()
        command = {"customer": "andrey-after-purchase", "order_number": 2042, "target_size": "XL"}
        with self.assertRaisesRegex(ShopError, "order_unavailable"):
            exchange_options(state, **{**command, "customer": "maria"})
        order = state["sampleOrders"]["2042"]
        order["collectedAt"] = (timezone.now() - timedelta(days=15)).isoformat()
        expired = exchange_options(state, **command)
        self.assertEqual((expired["outcome"], expired["reason"]), ("not_eligible", "expired"))
        self.assertEqual(exchange_options(state, **command, reason="defect")["outcome"], "staff_review")
        order["collectedAt"] = timezone.now().isoformat()
        state["stock"]["alpine:XL:center"] = 0
        self.assertEqual(exchange_options(state, **command)["outcome"], "available")
        with self.assertRaisesRegex(ShopError, "confirmation_required"):
            request_exchange(state, **command, store="gorki", confirmed=False)
        exchange = request_exchange(state, **command, store="gorki", confirmed=True)
        self.assertEqual((exchange["status"], state["stock"]["alpine:XL:gorki"]), ("requested", 1))
        self.assertEqual(state["refunds"], {})
        with self.assertRaisesRegex(ShopError, "refund_unavailable"):
            refund_payment(state, customer=command["customer"], order_number=2042, confirmed=True)
        with self.assertRaisesRegex(ShopError, "confirmation_required"):
            refund_payment(initial_state(), customer=command["customer"], order_number=2042, confirmed=False)

    def test_proposal_rechecks_stock_and_retains_the_confirmed_calculation(self):
        state = initial_state()
        request = {"quantities": {"M": 6, "L": 10, "XL": 4}, "city": "kazan", "budget": 35000}
        options = party_options(state, **request)["options"]
        self.assertEqual([option["available"] for option in options], [True, True, False])
        quote = prepare_party_quote(state, product_id="alpine", **request)
        details = {
            "quote_id": quote["id"], "company": "Высота", "contact": "Ирина",
            "email": "school@severny-veter.test", "address": "Казань", "confirmed": True,
        }
        state["wholesaleStock"]["alpine"]["XL"] = 3
        with self.assertRaisesRegex(ShopError, "party_stock_unavailable"):
            create_proposal(state, **details)
        state["wholesaleStock"]["alpine"]["XL"] = 4
        proposal = create_proposal(state, **details)
        self.assertEqual(proposal["quote"]["total"], 571600)
        self.assertEqual(state["wholesaleStock"]["alpine"]["XL"], 4)
        self.assertEqual(state["crm"][proposal["crmReference"]]["total"], proposal["quote"]["total"])
        self.assertEqual(state["mailbox"][proposal["number"]]["status"], "queued")


class NorthWindProposalDocumentTests(DomainEventTestBase):
    @patch.dict("os.environ", {"CHATBALLS_LOCAL_NORTH_WIND": "1"})
    def test_document_is_accessible_after_mail_failure_and_expires_on_reinstall(self):
        state = initial_state()
        quote = prepare_party_quote(state, product_id="alpine", quantities={"L": 4}, city="kazan")
        proposal = create_proposal(
            state, quote_id=quote["id"], company="<School>", contact="Irene",
            email="school@severny-veter.test", address="Kazan", confirmed=True,
        )
        state["mailbox"][proposal["number"]]["status"] = "failed"
        generation = uuid4()
        with tenant_atomic(self.context):
            dataset = DemoDataset.objects.create(
                organization=self.organization, status=DemoDatasetStatus.INSTALLED,
                generation=generation, shop_state=state,
            )
        path = proposal_path(self.context, generation, proposal["number"])
        client = TenantAPIClient()
        result = client.get(f"{path}?download=1")
        self.assertEqual(result.status_code, 200)
        self.assertIn("attachment; ", result["Content-Disposition"])
        self.assertContains(result, '<article class="document">')
        self.assertContains(result, "&lt;School&gt;")
        self.assertNotContains(result, "<script")
        with tenant_atomic(self.context):
            DemoDataset.objects.filter(pk=dataset.pk).update(generation=uuid4(), shop_state=initial_state())
        self.assertEqual(client.get(path).status_code, 404)
