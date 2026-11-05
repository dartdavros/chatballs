"""Staff mail selectors shared by the API and native actions."""

from rest_framework import serializers

from chatballs.api.pagination import cursor_id, window_size
from chatballs.conversations.access import require_conversation_action
from chatballs.conversations.email_attempt_models import EmailSendOperation
from chatballs.conversations.email_continuation import require_reply
from chatballs.conversations.email_options import available_mailboxes, saved_addresses
from chatballs.conversations.email_payloads import operation_payload
from chatballs.conversations.selectors import conversation_for_context


def options(context, conversation_id):
    conversation = conversation_for_context(context=context, conversation_id=conversation_id)
    require_reply(context, conversation, allow_unclaimed=True)
    return {
        "addresses": saved_addresses(conversation),
        "mailboxes": [{"id": connection.pk, "name": connection.name, "address": connection.config["email"]}
                      for connection in available_mailboxes(conversation.organization_id)],
    }


def operations(context, conversation_id, *, message_ids=None, before=None, limit=50):
    conversation = conversation_for_context(context=context, conversation_id=conversation_id)
    require_conversation_action(context, conversation, "conversations.view")
    limit = window_size({"limit": limit}, default=50)
    before = cursor_id({"before": before}, "before")
    if message_ids is not None:
        message_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=200).run_validation(
            message_ids.split(",") if isinstance(message_ids, str) and message_ids else [] if message_ids == "" else message_ids,
        )
    rows = EmailSendOperation.objects.filter(
        organization_id=conversation.organization_id, letter__thread__conversation=conversation,
    ).select_related("letter__thread", "letter__connection__channel", "initiated_by").order_by("-pk")
    if message_ids is not None:
        rows = rows.filter(letter__message_id__in=message_ids)
    if before is not None:
        rows = rows.filter(pk__lt=before)
    page = list(rows[:limit + 1])
    return {"items": [operation_payload(row, context=context) for row in page[:limit]],
            "nextCursor": page[limit - 1].pk if len(page) > limit else None}
