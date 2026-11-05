"""Opening and deleting a visible conversation preserve personal/domain effects."""

from rest_framework.exceptions import PermissionDenied

from chatballs.conversations.access import require_conversation_action
from chatballs.conversations.models import ConversationRead
from chatballs.conversations.selectors import conversation_for_context
from chatballs.conversations.services import delete_conversation
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.policy import can_administer_access, has_capability_any_scope


def require_inbox_access(context):
    if not has_capability_any_scope(context.membership, "conversations.view"):
        raise PermissionDenied(t("conversations.not_found"))


def visible_conversation(context, conversation_id):
    row = conversation_for_context(context=context, conversation_id=conversation_id)
    require_conversation_action(context, row, "conversations.view")
    return row


def open_conversation(context, conversation_id):
    row = visible_conversation(context, conversation_id)
    last_id = row.messages.order_by("-id").values_list("id", flat=True).first() or 0
    if last_id:
        read, created = ConversationRead.objects.get_or_create(conversation=row,
            user=context.actor_user, defaults={"last_read_message_id": last_id})
        if not created and read.last_read_message_id < last_id:
            read.last_read_message_id = last_id
            read.save(update_fields=["last_read_message_id", "updated_at"])
    return row


def remove_conversation(context, conversation_id, *, request=None):
    row = conversation_for_context(context=context, conversation_id=conversation_id)
    require_conversation_action(context, row, "conversations.operate")
    if not can_administer_access(context.membership):
        raise PermissionDenied({"detail": t("conversations.delete_admin_only")})
    record_audit_event(action="conversations.deleted", actor=context.actor_user,
        organization=context.organization, object_type="Conversation", object_id=str(row.pk), request=request)
    delete_conversation(context=context, conversation=row)
