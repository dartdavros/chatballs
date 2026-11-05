"""Original bounded public message history and template updates."""

from chatballs.api.pagination import cursor_id, window, window_payload, window_size
from chatballs.conversations.selectors import (
    MESSAGES_NEWER_KEYS,
    MESSAGES_OLDER_KEYS,
    conversation_messages,
)
from chatballs.conversations.serializers import message_payload
from chatballs.conversations.template_updates import add_template_updates

MESSAGE_WINDOW_SIZE = 50


def message_history(conversation, params):
    limit = window_size(params, default=MESSAGE_WINDOW_SIZE)
    messages = conversation_messages(conversation)
    after = cursor_id(params, "after")
    if after is not None:
        payload = window_payload(
            window(messages, keys=MESSAGES_NEWER_KEYS, limit=limit, after=after),
            message_payload,
        )
        add_template_updates(payload["items"], organization_id=conversation.organization_id)
        return payload
    page = window(
        messages,
        keys=MESSAGES_OLDER_KEYS,
        limit=limit,
        after=cursor_id(params, "before"),
    )
    # Курсор считается по окну «от свежих к старым» — это самое раннее
    # сообщение окна, с него продолжится прокрутка вверх. Наружу список
    # уходит в хронологическом порядке, как его рисует лента.
    payload = window_payload(page, message_payload)
    add_template_updates(payload["items"], organization_id=conversation.organization_id)
    payload["items"].reverse()
    return payload

