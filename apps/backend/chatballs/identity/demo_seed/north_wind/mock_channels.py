"""Local delivery for seeded channels. Failed or stale bindings are closed."""

from uuid import uuid4

from django.db import DatabaseError

from chatballs.identity.demo_seed.north_wind.state import ShopError, execute_write, read_state
from chatballs.tenancy.context import TenantContext


def _store_delivery(state, *, channel, kind, target, text, details):
    item = {
        "channel": channel, "kind": kind, "recipient": target,
        "text": text, "state": "sent", "details": details,
    }
    state["channelDeliveries"].append(item)
    return item


def is_available(context, integration):
    generation = integration.config.get("demoGeneration")
    if not integration.is_active or not generation:
        return False
    try:
        read_state(context, generation)
    except ShopError:
        return False
    return True


def deliver(integration, *, kind, target, text="", key=None, **details):
    generation = integration.config.get("demoGeneration")
    if not integration.is_active or not generation:
        return False
    try:
        execute_write(
            TenantContext.for_resource(integration.organization), generation, _store_delivery,
            key=key or str(uuid4()), lock_nowait=True,
            command={
                "channel": integration.provider, "kind": kind, "target": target,
                "text": text, "details": details,
            },
        )
    except (ShopError, DatabaseError):
        return False
    return True
