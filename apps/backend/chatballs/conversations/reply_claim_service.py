"""Employee reply claim, shared without an HTTP dependency."""

from uuid import UUID

from django.db import transaction
from rest_framework.exceptions import ValidationError

from chatballs.conversations.domain_events import is_accepted, operation_key
from chatballs.conversations.models import ControlMode
from chatballs.conversations.reply_access import lock_for_reply, require_human_reply
from chatballs.conversations.reply_audit import audit_reply
from chatballs.conversations.services import claim_conversation
from chatballs.i18n import t


def claim_reply(*, context, conversation_id, operation_id=None, request=None):
    """The original claim/check operation without a synthetic HTTP request."""
    if operation_id:
        try:
            UUID(str(operation_id))
        except (ValueError, TypeError, AttributeError) as error:
            raise ValidationError(t("transfers.operation_invalid")) from error
    conversation = lock_for_reply(context=context, conversation_id=conversation_id)
    if conversation.control_mode != ControlMode.HUMAN or (
        conversation.assigned_operator_id == context.actor_user.pk and not is_accepted(conversation)
    ):
        with transaction.atomic():
            conversation = claim_conversation(context=context, conversation_id=conversation.id,
                operation_id=operation_key("reply-claim", str(operation_id)) if operation_id else None)
        audit_reply(context, "claimed", conversation, request=request)
    require_human_reply(context=context, conversation=conversation)
    return conversation
