"""The six products and two pickup points from the ski-store case."""

from copy import deepcopy

SIZES = ("M", "L", "XL")
STORES = {
    "center": {"name": "Центр", "address": "Казань, ул. Спортивная, 12", "closesAt": 21},
    "gorki": {"name": "Горки", "address": "Казань, проспект Победы, 28", "closesAt": 22},
}
_ENGLISH_PICKUP_POINTS = {
    "center": ("Centre", "12 Sportivnaya Street, Kazan"),
    "gorki": ("Gorki", "28 Pobedy Avenue, Kazan"),
}

PRODUCTS = {
    key: {
        "id": key, "name": name, "basePrice": price, "insulation": insulation,
        "membrane": membrane, "breathability": breathability, "currency": "RUB",
    }
    for key, name, price, insulation, membrane, breathability in (
        ("alpine", "Alpine Pro", 29900, 120, 15000, 10000),
        ("summit", "Summit Light", 23900, 100, 10000, 8000),
        ("ridge", "Ridge Motion", 27900, 100, 15000, 12000),
        ("glacier", "Glacier Warm", 32900, 160, 20000, 15000),
        ("freeride", "Freeride Flow", 25900, 80, 15000, 15000),
        ("peak", "Peak Expert", 34900, 120, 20000, 20000),
    )
}

_STOCK_L = {
    "alpine": (3, 2), "summit": (4, 3), "ridge": (2, 4),
    "glacier": (3, 2), "freeride": (2, 3), "peak": (2, 1),
}


def stock_key(product_id, size, store):
    return f"{product_id}:{size}:{store}"


def initial_stock():
    stock = {}
    for product_id, (center, gorki) in _STOCK_L.items():
        for size, quantities in (
            ("M", (max(1, center - 1), max(1, gorki - 1))),
            ("L", (center, gorki)),
            ("XL", (max(1, center - 2), gorki)),
        ):
            stock.update({
                stock_key(product_id, size, store): count
                for store, count in zip(STORES, quantities, strict=True)
            })
    stock[stock_key("alpine", "XL", "center")] = 0
    return stock


def product_for(state, product_id):
    product = deepcopy(PRODUCTS[product_id])
    product["basePrice"] += state["priceAdjustments"].get(product_id, 0)
    product["personalPrice"] = (product["basePrice"] * 9 + 5) // 10
    return product


def pickup_point(state, store):
    info = STORES[store]
    if state.get("storefront", {}).get("language") == "en":
        name, address = _ENGLISH_PICKUP_POINTS[store]
        return {**info, "name": name, "address": address}
    return info


def availability(state, product_id, size):
    return [
        {"store": store, **pickup_point(state, store), "available": state["stock"][stock_key(product_id, size, store)]}
        for store in STORES
    ]


def available_choices(products):
    in_stock = [item for item in products if any(point["available"] for point in item["availability"])]
    return sorted(in_stock, key=lambda item: (-item["insulation"], item["basePrice"]))[:3]
