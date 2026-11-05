"""Media access follows the current visibility of its owning conversation."""

from chatballs.conversations.models import Message
from chatballs.conversations.selectors import conversation_for_context


def visible_message(context, message_id):
    message = Message.objects.select_related(
        "conversation", "conversation__channel", "conversation__connection",
    ).get(id=message_id, organization_id=context.organization_id)
    conversation_for_context(context=context, conversation_id=message.conversation_id)
    return message
