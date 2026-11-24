"""Cart pricing, reservation and customer-scoped order lookup."""

import hashlib
import json

from chatballs.identity.demo_seed.north_wind.catalog import (
    PRODUCTS,
    SIZES,
    STORES,
    pickup_point,
    product_for,
    stock_key,
)
from chatballs.identity.demo_seed.north_wind.state import ShopError


def quote_order(state, *, customer, product_id, size, bonus):
    if customer not in state["balances"]:
        raise ShopError("unknown_demo_customer")
    if product_id not in PRODUCTS or size not in SIZES:
        raise ShopError("unknown_product_variant")
    if type(bonus) is not int or bonus < 0:
        raise ShopError("invalid_bonus_amount")
    product = product_for(state, product_id)
    balance = state["balances"][customer]
    members = state.get("loyaltyMembers", ("andrey", "andrey-after-purchase"))
    price = product["personalPrice"] if customer in members else product["basePrice"]
    excluded = product_id in state["excludedFromBonuses"]
    limit = 0 if excluded else min(balance, price // 5)
    if bonus and excluded:
        raise ShopError("bonuses_unavailable")
    if bonus > limit:
        raise ShopError("bonus_limit")
    quote = {
        "customer": customer, "productId": product_id, "name": product["name"], "size": size,
        "personalPrice": price, "bonusBalance": balance,
        "maxBonus": limit, "bonusSpent": bonus, "total": price - bonus,
    }
    encoded = json.dumps(quote, sort_keys=True, separators=(",", ":")).encode()
    return {**quote, "revision": hashlib.sha256(encoded).hexdigest()}


def place_order(state, *, customer, product_id, size, bonus, store, revision, confirmed):
    if confirmed is not True:
        raise ShopError("confirmation_required")
    if store not in STORES:
        raise ShopError("unknown_pickup_point")
    quote = quote_order(state, customer=customer, product_id=product_id, size=size, bonus=bonus)
    if quote["revision"] != revision:
        raise ShopError("quote_changed")
    key = stock_key(product_id, size, store)
    if not state["stock"][key]:
        raise ShopError("stock_unavailable")

    number = state["nextOrder"]
    order = {
        **quote, "number": number, "store": store, "address": pickup_point(state, store)["address"],
        "status": "reserved", "balanceAfter": state["balances"][customer] - bonus,
        "stockAfter": state["stock"][key] - 1,
    }
    state["nextOrder"] += 1
    state["stock"][key] = order["stockAfter"]
    state["balances"][customer] = order["balanceAfter"]
    state["orders"][str(number)] = order
    return order


def find_order(state, *, customer, order_number):
    source = "sampleOrders" if customer in {"andrey-after-purchase", "pavel"} else "orders"
    order = state[source].get(str(order_number))
    if order is None or order["customer"] != customer:
        raise ShopError("order_unavailable")
    return order
