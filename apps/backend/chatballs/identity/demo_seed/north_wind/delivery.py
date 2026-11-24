"""Changes to fictional shipments and the corresponding demo events."""

from datetime import datetime, timedelta
from uuid import uuid4

from django.utils import timezone

from chatballs.identity.demo_seed.north_wind.catalog import pickup_point
from chatballs.identity.demo_seed.north_wind.orders import find_order
from chatballs.identity.demo_seed.north_wind.state import ShopError

TRANSITIONS = {
    "reserved": {"ready", "delayed"},
    "ready": {"collected", "delayed"},
    "delayed": {"ready"},
}


def shipment_status(state, *, customer, order_number):
    order = find_order(state, customer=customer, order_number=order_number)
    status = {"number": order["number"], "status": order["status"]}
    if order.get("eta"):
        status["eta"] = order["eta"]
    if order["status"] == "ready":
        pickup = pickup_point(state, order["store"])
        status["pickup"] = {"store": order["store"], **pickup}
    if customer == "pavel":
        changed = order.get("statusChangedAt")
        status["needsAttention"] = order["status"] != "collected" and (
            not changed or timezone.now() - datetime.fromisoformat(changed) > timedelta(days=1)
        )
    return status


def change_delivery(state, *, customer, order_number, status, confirmed):
    if confirmed is not True:
        raise ShopError("confirmation_required")
    order = find_order(state, customer=customer, order_number=order_number)
    if status not in TRANSITIONS.get(order["status"], ()):
        raise ShopError("invalid_delivery_transition")
    order["status"] = status
    order["statusChangedAt"] = timezone.now().isoformat()
    if status == "collected":
        order["collectedAt"] = order["statusChangedAt"]
    event = {
        "id": str(uuid4()), "type": "delivery.delayed" if status == "delayed" else "delivery.updated",
        "occurredAt": timezone.now().isoformat(), "orderNumber": order["number"], "status": status,
    }
    state["deliveries"][event["id"]] = event
    return event


def request_delivery_check(state, *, customer, order_number, confirmed, reference):
    if confirmed is not True:
        raise ShopError("confirmation_required")
    find_order(state, customer=customer, order_number=order_number)
    state.setdefault("deliveryChecks", {})[reference] = {
        "number": order_number, "readyAt": (timezone.now() + timedelta(seconds=3)).isoformat(),
    }
    return {"pending": True}


def delivery_check_result(state, *, customer, order_number, reference):
    check = state.get("deliveryChecks", {}).get(reference)
    if check is None or check["number"] != order_number:
        raise ShopError("delivery_check_unavailable")
    if timezone.now() < datetime.fromisoformat(check["readyAt"]):
        return {"pending": True}
    status = shipment_status(state, customer=customer, order_number=order_number)
    return {**status, "confirmedEta": bool(status.get("eta"))}


def settle_mail(state, *, proposal_number, status):
    mail = state["mailbox"].get(proposal_number)
    if mail is None or mail["status"] != "queued" or status not in {"sent", "failed", "unknown"}:
        raise ShopError("mail_transition_unavailable")
    mail["status"] = status
    return mail
