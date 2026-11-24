"""Quantity pricing, proposal and local CRM results."""

from datetime import datetime, timedelta
from uuid import uuid4

from django.utils import timezone

from chatballs.identity.demo_seed.north_wind.catalog import PRODUCTS, SIZES, product_for
from chatballs.identity.demo_seed.north_wind.state import ShopError

DELIVERY = {"kazan": (3500, 3), "innopolis": (4500, 4), "chelny": (6500, 5)}
MODELS = ("alpine", "ridge", "peak")


def _quantity(quantities):
    if not quantities or any(
        size not in SIZES or type(count) is not int or not 1 <= count <= 100
        for size, count in quantities.items()
    ):
        raise ShopError("invalid_party")
    quantity = sum(quantities.values())
    if quantity > 100:
        raise ShopError("invalid_party")
    return quantity


def party_options(state, *, quantities, city, budget=None):
    quantity = _quantity(quantities)
    if city not in DELIVERY:
        raise ShopError("invalid_party")
    options = []
    for key in MODELS:
        product = product_for(state, key)
        stock = state["wholesaleStock"][key]
        options.append({
            **product, "photo": f"/chat/north-wind/images/{key}.png",
            "stock": stock, "available": all(stock[size] >= count for size, count in quantities.items()),
            "withinBudget": budget is None or product["basePrice"] <= budget,
        })
    destinations = [{"id": key, "price": price, "days": days} for key, (price, days) in DELIVERY.items()]
    return {
        "quantity": quantity, "city": city, "options": options,
        "destinations": destinations,
    }


def quote_party(state, *, product_id, quantities, city, budget=None):
    if product_id not in PRODUCTS or city not in DELIVERY:
        raise ShopError("invalid_party")
    quantity = _quantity(quantities)
    available = state["wholesaleStock"][product_id]
    if any(count > available[size] for size, count in quantities.items()):
        raise ShopError("party_stock_unavailable")
    unit_price = product_for(state, product_id)["basePrice"]
    if budget is not None and unit_price > budget:
        raise ShopError("party_budget_exceeded")
    discounted_unit = unit_price * 95 // 100 if quantity >= 20 else unit_price
    delivery, days = DELIVERY[city]
    return {
        "productId": product_id, "productName": PRODUCTS[product_id]["name"],
        "quantities": quantities, "quantity": quantity, "city": city, "budget": budget,
        "unitPrice": unit_price, "discountedUnit": discounted_unit, "discountPercent": 5 if quantity >= 20 else 0,
        "subtotal": discounted_unit * quantity, "delivery": delivery, "days": days,
        "total": discounted_unit * quantity + delivery,
    }


def prepare_party_quote(state, *, product_id, quantities, city, budget=None):
    quote = quote_party(state, product_id=product_id, quantities=quantities, city=city, budget=budget)
    quote["validUntil"] = (timezone.now() + timedelta(minutes=20)).isoformat()
    quote["id"] = str(uuid4())
    state["partyQuotes"][quote["id"]] = quote
    return quote


def create_proposal(state, *, quote_id, company, contact, email, address, confirmed):
    if confirmed is not True:
        raise ShopError("confirmation_required")
    if not all(value.strip() for value in (company, contact, address)):
        raise ShopError("proposal_fields_required")
    quote = state["partyQuotes"].get(quote_id)
    if quote is None or timezone.now() > datetime.fromisoformat(quote["validUntil"]):
        raise ShopError("quote_changed")
    current = quote_party(
        state, product_id=quote["productId"], quantities=quote["quantities"], city=quote["city"],
        budget=quote.get("budget"),
    )
    if any(quote.get(key) != value for key, value in current.items()):
        raise ShopError("quote_changed")
    if any(item["quoteId"] == quote_id for item in state["proposals"].values()):
        raise ShopError("proposal_already_created")
    number = len(state["proposals"]) + 205
    result = {
        "number": f"KP-{number}", "crmReference": f"CRM-{number + 100}",
        "quoteId": quote_id, "quote": current, "company": company, "contact": contact,
        "email": email, "address": address,
        "validUntil": (timezone.now() + timedelta(days=7)).isoformat(),
    }
    state["proposals"][result["number"]] = result
    state["crm"][result["crmReference"]] = {
        "proposal": result["number"], "company": company, "contact": contact, "email": email,
        "assignee": "elena", "status": "open", "quantity": current["quantity"], "total": current["total"],
    }
    return result
