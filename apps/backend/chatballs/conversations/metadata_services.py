"""Conversation metadata operations shared by HTTP and native actions."""

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from chatballs.conversations.access import require_conversation_action
from chatballs.conversations.contact_card import save_card_fields
from chatballs.conversations.models import ConversationLabel, ConversationPriority
from chatballs.conversations.selectors import conversation_for_context
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.policy import can_administer_access


def _conversation(context, conversation_id, capability="conversations.operate"):
    row = conversation_for_context(context=context, conversation_id=conversation_id)
    require_conversation_action(context, row, capability)
    return row


def _audit(context, action, row, request):
    record_audit_event(action=f"conversations.{action}", actor=context.actor_user,
        organization=context.organization, object_type="Conversation", object_id=str(row.pk), request=request)


def set_priority(context, conversation_id, priority, *, request=None):
    row = _conversation(context, conversation_id)
    priority = str(priority).strip().upper()
    if priority not in ConversationPriority.values:
        raise ValidationError({"detail": t("conversations.unknown_priority")})
    row.priority = priority
    row.save(update_fields=["priority"])
    _audit(context, "priority_changed", row, request)
    return row


def change_contact(context, conversation_id, changes, *, request=None):
    row = _conversation(context, conversation_id)
    if row.contact is None:
        raise ValidationError({"detail": t("conversations.no_contact")})
    changed, error = save_card_fields(row.contact, changes)
    if error:
        raise ValidationError({"detail": error})
    if changed:
        _audit(context, "contact_updated", row, request)
    return row


def set_note(context, conversation_id, note):
    row = _conversation(context, conversation_id, "conversations.comment")
    note = str(note)
    if len(note) > 4000:
        raise ValidationError({"detail": t("conversations.note_too_long")})
    row.note, row.note_author = note, context.actor_user if note else None
    row.note_updated_at = timezone.now() if note else None
    row.save(update_fields=["note", "note_author", "note_updated_at"])
    return row


def set_labels(context, conversation_id, label_ids):
    row = _conversation(context, conversation_id)
    if not isinstance(label_ids, list) or not all(isinstance(pk, int) for pk in label_ids):
        raise ValidationError({"detail": t("conversations.label_ids_list")})
    labels = list(ConversationLabel.objects.filter(organization_id=context.organization_id, pk__in=set(label_ids)))
    if len(labels) != len(set(label_ids)):
        raise ValidationError({"detail": t("conversations.unknown_label")})
    row.labels.set(labels)
    return row


def set_archived(context, conversation_id, archived, *, request=None):
    row = _conversation(context, conversation_id)
    if not isinstance(archived, bool):
        raise ValidationError({"detail": t("conversations.archived_boolean")})
    if not archived and not can_administer_access(context.membership):
        raise PermissionDenied({"detail": t("conversations.restore_admin_only")})
    row.archived_at = timezone.now() if archived else None
    row.save(update_fields=["archived_at"])
    _audit(context, "archived" if archived else "unarchived", row, request)
    return row
