"""Customer operations shared by the storefront and the local mock shop."""

from chatballs.identity.demo_seed.north_wind.catalog import (
    PRODUCTS,
    SIZES,
    availability,
    product_for,
)
from chatballs.identity.demo_seed.north_wind.orders import place_order, quote_order
from chatballs.identity.demo_seed.north_wind.state import ShopError


def storefront_data(state, *, customer):
    configuration = state.get("storefront")
    if configuration is None or customer not in state["balances"]:
        raise ShopError("demo_generation_unavailable")
    pickup = state.get("pickupSite") if customer == "maria" else None
    loyalty = state.get("loyaltySite") if customer == "andrey" and customer in state.get("loyaltyMembers", ()) else None
    cart = state.get("carts", {}).get(customer)
    return {
        "widgetKey": (pickup or loyalty or configuration)["widgetKey"],
        "pickupEvent": pickup["eventName"] if pickup else None,
        "loyaltyWidget": loyalty["widgetKey"] if loyalty else None,
        "loyaltyEvent": loyalty["eventName"] if loyalty and state["balances"][customer] == 1500 else None,
        "language": configuration["language"],
        "customer": customer,
        "balance": state["balances"][customer],
        "cart": cart,
        "order": _checkout_receipt(state, customer) if cart is None else None,
        "products": [
            {
                **product_for(state, key),
                "stock": {size: availability(state, key, size) for size in SIZES},
            }
            for key in PRODUCTS
        ],
    }


def _checkout_receipt(state, customer):
    number = state.get("lastCheckouts", {}).get(customer)
    if number is None:
        # Existing generations retain the original response in the idempotency journal.
        number = max((
            request["result"]["number"] for key, request in state["requests"].items()
            if key.startswith("submit_cart:") and request["command"].get("customer") == customer
        ), default=None)
    order = state["orders"].get(str(number))
    return order if order and order["customer"] == customer else None


def prepare_cart(state, *, customer, product_id, size):
    quote = quote_order(state, customer=customer, product_id=product_id, size=size, bonus=0)
    cart = {"productId": product_id, "size": size, "personalPrice": quote["personalPrice"]}
    state.setdefault("carts", {})[customer] = cart
    return cart


def submit_cart(state, *, customer, product_id, size, bonus, store, revision, confirmed):
    carts = state.setdefault("carts", {})
    cart = carts.get(customer)
    if not cart or (cart["productId"], cart["size"]) != (product_id, size):
        raise ShopError("cart_changed")
    order = place_order(
        state, customer=customer, product_id=product_id, size=size, bonus=bonus,
        store=store, revision=revision, confirmed=confirmed,
    )
    del carts[customer]
    state.setdefault("lastCheckouts", {})[customer] = order["number"]
    return order
