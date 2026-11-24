"""Signature and scope shared by local mock readers."""

import os

from django.core import signing

from chatballs.identity.demo_seed.north_wind.state import ShopError

_SALT = "north-wind-demo-local-read"


def local_demo_enabled():
    return os.environ.get("CHATBALLS_LOCAL_NORTH_WIND") == "1"


def issue_local_read_token(dataset, *, customer):
    if not dataset.generation or customer not in dataset.shop_state.get("balances", {}):
        raise ShopError("demo_generation_unavailable")
    return signing.dumps({
        "organization": dataset.organization_id,
        "generation": str(dataset.generation),
        "customer": customer,
    }, salt=_SALT)


def read_local_binding(headers):
    scheme, _, value = headers.get("Authorization", "").partition(" ")
    if scheme != "Bearer" or not value:
        return None
    try:
        return signing.loads(value, salt=_SALT)
    except signing.BadSignature:
        return None
