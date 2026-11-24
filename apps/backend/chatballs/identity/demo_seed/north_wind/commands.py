"""Typed commands for the locally hosted mock business system."""

from rest_framework import serializers

from chatballs.identity.demo_seed.north_wind.after_sales import (
    EXCHANGE_REASONS,
    exchange_options,
    refund_payment,
    request_exchange,
)
from chatballs.identity.demo_seed.north_wind.appointments import book_fitting, fitting_slots
from chatballs.identity.demo_seed.north_wind.catalog import (
    PRODUCTS,
    SIZES,
    STORES,
    availability,
    product_for,
)
from chatballs.identity.demo_seed.north_wind.delivery import (
    change_delivery,
    settle_mail,
    shipment_status,
)
from chatballs.identity.demo_seed.north_wind.loyalty_cases import LOYALTY_CASES, select_loyalty_case
from chatballs.identity.demo_seed.north_wind.orders import find_order, place_order, quote_order
from chatballs.identity.demo_seed.north_wind.wholesale import (
    DELIVERY,
    create_proposal,
    party_options,
    prepare_party_quote,
)


class CatalogInput(serializers.Serializer):
    query = serializers.CharField(max_length=120, allow_blank=True, default="")
    size = serializers.ChoiceField(choices=SIZES, default="L")
    budget = serializers.IntegerField(min_value=0, required=False)


class ProductInput(serializers.Serializer):
    product_id = serializers.ChoiceField(choices=PRODUCTS)
    size = serializers.ChoiceField(choices=SIZES, default="L")


def lookup_product(state, *, product_id, size):
    return {**product_for(state, product_id), "availability": availability(state, product_id, size)}


def search_catalog(state, *, query, size, budget=None):
    words = query.lower().split()
    products = []
    for key in PRODUCTS:
        product = product_for(state, key)
        if not all(word in product["name"].lower() for word in words):
            continue
        if budget is not None and product["basePrice"] > budget:
            continue
        products.append({**product, "availability": availability(state, key, size)})
    return {"products": products}


class QuoteInput(serializers.Serializer):
    customer = serializers.CharField(max_length=64)
    product_id = serializers.ChoiceField(choices=PRODUCTS)
    size = serializers.ChoiceField(choices=SIZES)
    bonus = serializers.IntegerField(min_value=0, default=0)


class OrderInput(QuoteInput):
    store = serializers.ChoiceField(choices=STORES)
    revision = serializers.CharField(min_length=64, max_length=64)
    confirmed = serializers.BooleanField()


class OrderLookup(serializers.Serializer):
    customer = serializers.CharField(max_length=64)
    order_number = serializers.IntegerField(min_value=1)


class ExchangeOptionsInput(OrderLookup):
    target_size = serializers.ChoiceField(choices=SIZES)
    reason = serializers.ChoiceField(choices=EXCHANGE_REASONS, default="size")


class ExchangeInput(ExchangeOptionsInput):
    store = serializers.ChoiceField(choices=STORES, required=False)
    confirmed = serializers.BooleanField()


class RefundInput(OrderLookup):
    confirmed = serializers.BooleanField()


class DeliveryInput(OrderLookup):
    status = serializers.ChoiceField(choices=("ready", "delayed", "collected"))
    confirmed = serializers.BooleanField()


class SlotsInput(serializers.Serializer):
    store = serializers.ChoiceField(choices=STORES)
    day = serializers.DateField()


class FittingInput(serializers.Serializer):
    customer = serializers.CharField(max_length=64)
    store = serializers.ChoiceField(choices=STORES)
    starts_at = serializers.CharField(max_length=40)
    products = serializers.ListField(child=serializers.ChoiceField(choices=PRODUCTS), min_length=2, max_length=2)
    confirmed = serializers.BooleanField()


class PartyOptionsInput(serializers.Serializer):
    quantities = serializers.DictField(child=serializers.IntegerField(min_value=1, max_value=100))
    city = serializers.ChoiceField(choices=DELIVERY)
    budget = serializers.IntegerField(min_value=0, required=False)


class PartyInput(PartyOptionsInput):
    product_id = serializers.ChoiceField(choices=PRODUCTS)


class ProposalInput(serializers.Serializer):
    quote_id = serializers.CharField(max_length=36)
    company = serializers.CharField(max_length=120)
    contact = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    address = serializers.CharField(max_length=240)
    confirmed = serializers.BooleanField()


class MailInput(serializers.Serializer):
    proposal_number = serializers.CharField(max_length=32)
    status = serializers.ChoiceField(choices=("sent", "failed", "unknown"))


class LoyaltyCaseInput(serializers.Serializer):
    case = serializers.ChoiceField(choices=LOYALTY_CASES)


READ_COMMANDS = {
    "catalog": (CatalogInput, search_catalog),
    "product": (ProductInput, lookup_product),
    "order-quote": (QuoteInput, quote_order),
    "order-status": (OrderLookup, find_order),
    "shipment-status": (OrderLookup, shipment_status),
    "exchange-options": (ExchangeOptionsInput, exchange_options),
    "party-options": (PartyOptionsInput, party_options),
    "fitting-slots": (SlotsInput, fitting_slots),
}
WRITE_COMMANDS = {
    "order": (OrderInput, place_order),
    "exchange": (ExchangeInput, request_exchange),
    "refund": (RefundInput, refund_payment),
    "delivery": (DeliveryInput, change_delivery),
    "fitting": (FittingInput, book_fitting),
    "party-quote": (PartyInput, prepare_party_quote),
    "proposal": (ProposalInput, create_proposal),
    "mail-result": (MailInput, settle_mail),
    "loyalty-case": (LoyaltyCaseInput, select_loyalty_case),
}
