"""Local exchange policy and separate demo payment refunds."""

from datetime import datetime, timedelta

from django.utils import timezone

from chatballs.identity.demo_seed.north_wind.catalog import (
    SIZES,
    STORES,
    availability,
    pickup_point,
    stock_key,
)
from chatballs.identity.demo_seed.north_wind.orders import find_order
from chatballs.identity.demo_seed.north_wind.state import ShopError

EXCHANGE_REASONS = ("size", "defect")
EXCHANGE_DAYS = 14


def exchange_options(state, *, customer, order_number, target_size, reason="size"):
    order = find_order(state, customer=customer, order_number=order_number)
    if target_size not in SIZES or reason not in EXCHANGE_REASONS:
        raise ShopError("exchange_unavailable")
    stores = availability(state, order["productId"], target_size)
    received = order.get("collectedAt")
    expired = received and timezone.now() - datetime.fromisoformat(received) > timedelta(days=EXCHANGE_DAYS)
    if reason == "defect":
        outcome = "staff_review"
    elif order["status"] != "collected" or expired or order["size"] == target_size:
        outcome = "not_eligible"
    else:
        outcome = "available" if any(item["available"] for item in stores) else "out_of_stock"
    result = {"orderNumber": order_number, "targetSize": target_size, "outcome": outcome,
              "exchangeDays": EXCHANGE_DAYS, "pickupPoints": stores, "originalStore": order["store"]}
    if expired and outcome == "not_eligible":
        result["reason"] = "expired"
    return result


def request_exchange(state, *, customer, order_number, target_size, confirmed, reason="size", store=None):
    if confirmed is not True:
        raise ShopError("confirmation_required")
    options = exchange_options(
        state, customer=customer, order_number=order_number, target_size=target_size, reason=reason,
    )
    if options["outcome"] != "available":
        raise ShopError({"staff_review": "staff_review", "out_of_stock": "stock_unavailable"}.get(
            options["outcome"], "exchange_unavailable",
        ))
    order = find_order(state, customer=customer, order_number=order_number)
    order_key = f"{order['customer']}:{order_number}"
    if order_key in state["exchanges"]:
        raise ShopError("exchange_already_requested")
    if order_key in state.get("refunds", {}):
        raise ShopError("exchange_unavailable")
    point = store or order["store"]
    if point not in STORES:
        raise ShopError("unknown_pickup_point")
    key = stock_key(order["productId"], target_size, point)
    if not state["stock"][key]:
        raise ShopError("stock_unavailable")
    exchange = {
        "number": len(state["exchanges"]) + 1, "orderNumber": order_number,
        "targetSize": target_size, "store": point, "status": "requested", "address": pickup_point(state, point)["address"],
    }
    state["stock"][key] -= 1
    state["exchanges"][order_key] = exchange
    return exchange


def refund_payment(state, *, customer, order_number, confirmed):
    if confirmed is not True:
        raise ShopError("confirmation_required")
    order = find_order(state, customer=customer, order_number=order_number)
    key = f"{order['customer']}:{order_number}"
    refunds = state.setdefault("refunds", {})
    if order["status"] != "collected" or key in state["exchanges"] or key in refunds:
        raise ShopError("refund_unavailable")
    payment = {
        "number": len(refunds) + 1, "orderNumber": order_number, "amount": order["total"],
        "bonusesRestored": order["bonusSpent"], "status": "refunded",
    }
    state["balances"][order["customer"]] += payment["bonusesRestored"]
    refunds[key] = payment
    return payment
