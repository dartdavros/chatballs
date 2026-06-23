import logging
from typing import Callable

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict], None]
_REGISTRY: dict[str, EventHandler] = {}


def register(event_type: str) -> Callable[[EventHandler], EventHandler]:
    def decorator(handler: EventHandler) -> EventHandler:
        _REGISTRY[event_type] = handler
        return handler

    return decorator


def dispatch(event_type: str, payload: dict) -> None:
    handler = _REGISTRY.get(event_type)
    if handler is None:
        logger.info("No handler registered for event %s", event_type)
        return
    handler(payload)
