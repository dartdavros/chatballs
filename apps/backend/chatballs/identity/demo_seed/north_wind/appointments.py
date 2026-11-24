"""Availability of fitting slots in Moscow time."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from chatballs.identity.demo_seed.north_wind.catalog import PRODUCTS, STORES, pickup_point
from chatballs.identity.demo_seed.north_wind.state import ShopError

MOSCOW = ZoneInfo("Europe/Moscow")
FITTING_DURATION = timedelta(minutes=45)
SLOT_INTERVAL = timedelta(minutes=30)


def fitting_slots(state, *, store, day, now=None):
    if store not in STORES:
        raise ShopError("unknown_pickup_point")
    current = (now or timezone.now()).astimezone(MOSCOW)
    if not current.date() <= day <= current.date() + timedelta(days=7):
        raise ShopError("fitting_date_unavailable")
    slot = datetime.combine(day, time(10), MOSCOW)
    closes = datetime.combine(day, time(STORES[store]["closesAt"]), MOSCOW)
    bookings = [
        datetime.fromisoformat(booking["startsAt"])
        for booking in state["bookings"].values() if booking["store"] == store
    ]
    slots = []
    while slot + FITTING_DURATION <= closes:
        if slot > current and not any(abs(slot - booked) < FITTING_DURATION for booked in bookings):
            slots.append(slot.isoformat())
        slot += SLOT_INTERVAL
    return slots


def book_fitting(state, *, customer, store, starts_at, products, confirmed, contact_phone=None):
    if confirmed is not True:
        raise ShopError("confirmation_required")
    if customer not in state["balances"]:
        raise ShopError("unknown_demo_customer")
    if len(products) != 2 or len(set(products)) != 2 or any(item not in PRODUCTS for item in products):
        raise ShopError("invalid_fitting_products")
    try:
        start = datetime.fromisoformat(starts_at)
    except ValueError as error:
        raise ShopError("fitting_date_unavailable") from error
    if start.tzinfo is None:
        raise ShopError("fitting_date_unavailable")
    local = start.astimezone(MOSCOW)
    if local.isoformat() not in fitting_slots(state, store=store, day=local.date()):
        raise ShopError("fitting_slot_unavailable")
    event = {
        "number": len(state["bookings"]) + 2043, "customer": customer, "store": store,
        "startsAt": local.isoformat(), "minutes": 45, "products": products,
        "address": pickup_point(state, store)["address"], "status": "confirmed",
    }
    if contact_phone:
        event["contactPhone"] = contact_phone
    state["bookings"][str(event["number"])] = event
    return event
