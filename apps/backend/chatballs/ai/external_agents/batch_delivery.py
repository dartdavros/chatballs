"""Publish the already validated native messages, preserving one item per receipt."""

from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.normalization import current
from chatballs.ai.external_agents.state import applicable
from chatballs.conversations.ai_reply_delivery import bind_email_reply, record_reply
from chatballs.conversations.models import Message, MessageAuthor


def publish(context, row, conversation, delivery, normalized, route, item_state):
    result = []
    for identifier, fields in normalized:
        if not applicable(row, context):
            raise ValueError("control_changed")
        message = Message(conversation=conversation, author_type=MessageAuthor.AI, **fields)
        current(message, row)
        message.save()
        bind_email_reply(message, route)
        if not conversation.is_test:
            record_reply(message)
        ExternalAgentDeliveryItem.objects.create(delivery=delivery, public_id=identifier,
            position=len(result), message=message, state=item_state)
        result.append({"itemId": identifier, "messageId": str(message.pk), "state": item_state})
    return result
