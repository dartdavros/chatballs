"""ID-only jobs use the existing worker-events registry and transactional outbox."""

from chatballs.ai.external_agents import delivery, dispatch
from chatballs.ai.external_agents.state import DELIVER, WAKE
from chatballs.events.handlers import register


@register(WAKE, manages_own_transaction=True)
def wake(payload, context):
    if context is not None:
        dispatch.run(context, payload["conversationId"])


@register(DELIVER, manages_own_transaction=True)
def deliver(payload, context):
    if context is not None:
        delivery.run(context, payload["conversationId"])
