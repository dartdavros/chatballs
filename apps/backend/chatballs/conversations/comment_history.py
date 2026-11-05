"""Protected internal history for HTTP and native actions."""

from chatballs.api.pagination import cursor_id, window, window_payload, window_size
from chatballs.conversations.audience import ConversationAudience
from chatballs.conversations.comment_access import comment_conversation
from chatballs.conversations.history_selectors import conversation_records
from chatballs.conversations.selectors import MESSAGES_NEWER_KEYS, MESSAGES_OLDER_KEYS
from chatballs.identity.avatars import user_avatar_url_in


def comment_payload(comment):
    return {"id": comment.pk, "conversationId": comment.conversation_id,
        "audience": comment.audience, "text": comment.text,
        "author": {"id": comment.author_id,
            "name": comment.author.full_name or comment.author.email,
            "avatarUrl": user_avatar_url_in(comment.author, comment.organization_id)},
        "createdAt": comment.created_at.isoformat(), "operationId": str(comment.operation_id)}


def comment_history(*, context, conversation_id, parameters):
    conversation = comment_conversation(context=context, conversation_id=conversation_id)
    records = conversation_records(conversation, audience=ConversationAudience.INTERNAL)
    after = cursor_id(parameters, "after")
    page = window(records, keys=MESSAGES_NEWER_KEYS if after is not None else MESSAGES_OLDER_KEYS,
        limit=window_size(parameters),
        after=after if after is not None else cursor_id(parameters, "before"))
    payload = window_payload(page, comment_payload)
    if after is None:
        payload["items"].reverse()
    return payload
