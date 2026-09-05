import logging
from typing import Callable

from chatballs.events.models import OutboxEvent
from chatballs.events.services import tenant_context_for_event
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic

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
    context = tenant_context_for_event(event)
    if context is None:
        handler(event.payload, None)
        return
    with tenant_atomic(context):
        handler(event.payload, context)
