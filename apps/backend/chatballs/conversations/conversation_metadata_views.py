"""Дизайн-базлайн v2: приоритет, метки, заметка, архив, шаблоны, счётчики.

Решения владельца (2026-09-04): метки и приоритет входят в модель; «удалить
диалог» = архив, архив видят только администраторы; шаблоны ответов общие на
организацию (редактируют администраторы, используют все).
"""

from __future__ import annotations

from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.conversations.contact_card import save_card_fields
from chatballs.conversations.models import (
    Conversation,
    ConversationLabel,
    ConversationPriority,
)
from chatballs.conversations.serializers import conversation_payload
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t
from chatballs.identity.policy import can_administer_access


class ConversationPriorityView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(
                request, conversation_id, self.required_capability
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        priority = str(request.data.get("priority", "")).strip().upper()
        if priority not in ConversationPriority.values:
            return Response({"detail": t("conversations.unknown_priority")}, status=400)
        conversation.priority = priority
        conversation.save(update_fields=["priority"])
        self._audit(request, "priority_changed", conversation)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation, detailed=True, viewer_id=request.user.id
                )
            }
        )


class ConversationContactView(ConversationViewBase):
    """Карточка контакта из диалога (дизайн-базлайн v2, карандаш у имени):
    имя, описание, телефон, почта, компания, город."""

    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(
                request, conversation_id, self.required_capability
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        contact = conversation.contact
        if contact is None:
            return Response({"detail": t("conversations.no_contact")}, status=400)
        changed, error = save_card_fields(contact, request.data)
        if error:
            return Response({"detail": error}, status=400)
        if changed:
            self._audit(request, "contact_updated", conversation)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation, detailed=True, viewer_id=request.user.id
                )
            }
        )


class ConversationNoteView(ConversationViewBase):
    required_capability = "conversations.comment"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(
                request, conversation_id, self.required_capability
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        note = str(request.data.get("note", ""))
        if len(note) > 4000:
            return Response({"detail": t("conversations.note_too_long")}, status=400)
        conversation.note = note
        conversation.note_author = request.user if note else None
        conversation.note_updated_at = timezone.now() if note else None
        conversation.save(update_fields=["note", "note_author", "note_updated_at"])
        return Response(
            {
                "conversation": conversation_payload(
                    conversation, detailed=True, viewer_id=request.user.id
                )
            }
        )


class ConversationLabelsView(ConversationViewBase):
    """Полная замена набора меток диалога (чипы в карточке)."""

    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(
                request, conversation_id, self.required_capability
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        label_ids = request.data.get("labelIds")
        if not isinstance(label_ids, list) or not all(
            isinstance(item, int) for item in label_ids
        ):
            return Response({"detail": t("conversations.label_ids_list")}, status=400)
        labels = list(
            ConversationLabel.objects.filter(
                organization_id=request.tenant_context.organization_id,
                id__in=set(label_ids),
            )
        )
        if len(labels) != len(set(label_ids)):
            return Response({"detail": t("conversations.unknown_label")}, status=400)
        conversation.labels.set(labels)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation, detailed=True, viewer_id=request.user.id
                )
            }
        )


class ConversationArchiveView(ConversationViewBase):
    """«Удалить диалог» = архив: скрыт из списков, восстановить может только
    администратор."""

    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(
                request, conversation_id, self.required_capability
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        archived = request.data.get("archived")
        if not isinstance(archived, bool):
            return Response({"detail": t("conversations.archived_boolean")}, status=400)
        if not archived and not can_administer_access(request.tenant_context.membership):
            return Response(
                {"detail": t("conversations.restore_admin_only")}, status=403
            )
        conversation.archived_at = timezone.now() if archived else None
        conversation.save(update_fields=["archived_at"])
        self._audit(request, "archived" if archived else "unarchived", conversation)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation, detailed=True, viewer_id=request.user.id
                )
            }
        )
