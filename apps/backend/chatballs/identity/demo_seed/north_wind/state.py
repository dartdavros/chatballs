"""Storage shared by the local mock protocols and the reinstall operation."""

from datetime import timedelta

from django.utils import timezone

from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.north_wind.catalog import PRODUCTS, initial_stock
from chatballs.tenancy.database import tenant_atomic


class ShopError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def initial_state():
    now = timezone.now()
    return {
        "datasetName": "north-wind",
        "balances": {"andrey": 1500, "andrey-after-purchase": 750, "maria": 0, "olga": 0, "pavel": 0, "school": 0},
        "loyaltyMembers": ["andrey", "andrey-after-purchase"],
        "priceAdjustments": {},
        "excludedFromBonuses": [],
        "stock": initial_stock(),
        "nextOrder": 2048,
        "orders": {},
        "sampleOrders": {
            "2042": {
                "number": 2042, "customer": "andrey-after-purchase", "productId": "alpine",
                "size": "L", "store": "center", "status": "collected", "total": 26160,
                "bonusSpent": 750, "name": "Alpine Pro", "collectedAt": (now - timedelta(days=2)).isoformat(),
            },
            "2043": {
                "number": 2043, "customer": "pavel", "productId": "ridge",
                "size": "L", "store": "gorki", "status": "reserved", "total": 27900,
                "bonusSpent": 0, "name": "Ridge Motion",
            },
            "2044": {
                "number": 2044, "customer": "andrey-after-purchase", "productId": "summit",
                "size": "L", "store": "center", "status": "ready", "total": 23900,
                "bonusSpent": 0, "name": "Summit Light",
            },
            "2045": {
                "number": 2045, "customer": "andrey-after-purchase", "productId": "ridge",
                "size": "L", "store": "gorki", "status": "delayed", "total": 27900,
                "bonusSpent": 0, "name": "Ridge Motion",
            },
            "2046": {
                "number": 2046, "customer": "andrey-after-purchase", "productId": "glacier",
                "size": "L", "store": "gorki", "status": "collected", "total": 32900,
                "bonusSpent": 0, "name": "Glacier Warm", "collectedAt": (now - timedelta(days=16)).isoformat(),
            },
            "2047": {
                "number": 2047, "customer": "andrey-after-purchase", "productId": "freeride",
                "size": "M", "store": "center", "status": "collected", "total": 23310,
                "bonusSpent": 0, "name": "Freeride Flow", "collectedAt": (now - timedelta(days=1)).isoformat(),
            },
        },
        "deliveryChecks": {},
        "bookings": {},
        "exchanges": {},
        "refunds": {},
        "proposals": {},
        "partyQuotes": {},
        "wholesaleStock": {
            product_id: {"M": 12, "L": 14, "XL": 10 if product_id != "peak" else 0}
            for product_id in PRODUCTS
        },
        "crm": {},
        "deliveries": {},
        "channelDeliveries": [],
        "requests": {},
    }


def read_state(context, generation):
    with tenant_atomic(context):
        dataset = _dataset_query(context, generation).first()
        if dataset is None or not dataset.shop_state:
            raise ShopError("demo_generation_unavailable")
        return dataset.shop_state


def execute_write(context, generation, operation, *, key, command, lock_nowait=False):
    if not key or len(key) > 128:
        raise ShopError("idempotency_key_required")
    with tenant_atomic(context):
        dataset = _dataset_query(context, generation).select_for_update(nowait=lock_nowait).first()
        if dataset is None or not dataset.shop_state:
            raise ShopError("demo_generation_unavailable")
        state = dataset.shop_state
        request_key = f"{operation.__name__}:{key}"
        previous = state["requests"].get(request_key)
        if previous:
            if previous["command"] != command:
                raise ShopError("idempotency_conflict")
            return previous["result"]
        result = operation(state, **command)
        state["requests"][request_key] = {"command": command, "result": result}
        dataset.save(update_fields=["shop_state"])
        return result


def _dataset_query(context, generation):
    return DemoDataset.objects.filter(
        organization_id=context.organization_id, generation=generation,
        status__in=(DemoDatasetStatus.INSTALLED, DemoDatasetStatus.REINSTALLING),
    )
