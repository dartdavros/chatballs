"""Switch the live mock-shop terms for the approved bonus branches."""

from chatballs.identity.demo_seed.north_wind.orders import quote_order
from chatballs.identity.demo_seed.north_wind.state import ShopError

LOYALTY_CASES = ("standard", "balance-600", "price-plus-2000", "excluded")


def select_loyalty_case(state, *, case):
    if any(order["customer"] == "andrey" for order in state["orders"].values()):
        raise ShopError("loyalty_case_requires_reinstall")
    state["balances"]["andrey"] = 600 if case == "balance-600" else 1500
    state["priceAdjustments"].pop("alpine", None)
    if case == "price-plus-2000":
        state["priceAdjustments"]["alpine"] = 2000
    exclusions = [product for product in state["excludedFromBonuses"] if product != "alpine"]
    if case == "excluded":
        exclusions.append("alpine")
    state["excludedFromBonuses"] = exclusions
    return {"case": case, "bonusesAllowed": case != "excluded",
            **quote_order(state, customer="andrey", product_id="alpine", size="L", bonus=0)}


def loyalty_profile(state, *, customer, product_id):
    if customer != "andrey" or customer not in state["loyaltyMembers"]:
        raise ShopError("profile_unavailable")
    quote = quote_order(state, customer=customer, product_id=product_id, size="L", bonus=0)
    language = state.get("historyLanguage", "ru")
    return {"language": language, "product": product_id, "balance": quote["bonusBalance"],
            "personalPrice": quote["personalPrice"], "allowed": product_id not in state["excludedFromBonuses"],
            "maxBonus": quote["maxBonus"]}
