import logging
from typing import Callable

from hub_platform.events.models import OutboxEvent
from hub_platform.events.services import tenant_context_for_event
from hub_platform.tenancy.context import TenantContext

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict, TenantContext | None], None]
_REGISTRY: dict[str, EventHandler] = {}


def register(event_type: str) -> Callable[[EventHandler], EventHandler]:
    def decorator(handler: EventHandler) -> EventHandler:
        _REGISTRY[event_type] = handler
        return handler

    return decorator


def dispatch(event: OutboxEvent) -> None:
    handler = _REGISTRY.get(event.event_type)
    if handler is None:
        logger.info("No handler registered for event %s", event.event_type)
        return
    handler(event.payload, tenant_context_for_event(event))
