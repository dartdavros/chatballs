"""Allowed demo values for a North Wind site selection."""

PICKUP_EVENT = "north-wind.pickup-selection"
PICKUP_TASK = "Offer North Wind pickup advice using the catalogue and the selected size and budget."
PICKUP_BUDGET_LIMIT = 1_000_000
PICKUP_CATEGORY = "ski-suits"
PICKUP_CITY = "kazan"


def catalogue_selection(data):
    if not isinstance(data, dict) or data.keys() != {"category", "city", "size", "budget", "store"}:
        return None
    if (data["category"] != PICKUP_CATEGORY or data["city"] != PICKUP_CITY
            or data["size"] not in ("M", "L", "XL")
            or data["store"] not in ("center", "gorki")
            or type(data["budget"]) is not int or not 0 <= data["budget"] <= PICKUP_BUDGET_LIMIT):
        return None
    return {key: data[key] for key in ("size", "budget", "store")}
