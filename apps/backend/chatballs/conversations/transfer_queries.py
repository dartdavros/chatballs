"""Protected bounded transfer history and current reason choices."""

from rest_framework.exceptions import NotFound

from chatballs.api.pagination import page_payload, paginate
from chatballs.conversations.access import require_conversation_action
from chatballs.conversations.selectors import conversation_for_context
from chatballs.conversations.transfer_display import transfer_history_payload
from chatballs.conversations.transfer_models import ConversationTransfer, TransferReason
from chatballs.conversations.transfer_reason_payloads import reason_option_payload
from chatballs.i18n import t


def transfer_history(context, conversation_id, params, *, transfer_id=None):
    conversation = conversation_for_context(context=context, conversation_id=conversation_id)
    require_conversation_action(context, conversation, "conversations.view")
    rows = ConversationTransfer.objects.filter(organization_id=context.organization_id,
        conversation=conversation).select_related("reason", "initiated_by", "previous_operator",
            "new_operator", "conversation__contact", "conversation__connection").order_by("-occurred_at", "-id")
    if transfer_id is None:
        return page_payload(paginate(rows, params), transfer_history_payload)
    row = rows.filter(pk=transfer_id).first()
    if row is None:
        raise NotFound({"detail": t("conversations.not_found")})
    return {"transfer": transfer_history_payload(row)}


def transfer_options(context, conversation_id, params):
    conversation = conversation_for_context(context=context, conversation_id=conversation_id)
    require_conversation_action(context, conversation, "conversations.assign")
    reasons = TransferReason.objects.filter(organization_id=context.organization_id, is_active=True)
    return page_payload(paginate(reasons, params), reason_option_payload)
