"""Объединение и разъединение контактов (ADR-CHATBALLS-0006).

Автоматически идентичности разных подключений не объединяются. Объединение —
ручная операция владельца: требует причины, переносит идентичности и диалоги,
полностью аудируется и разворачивается обратно. Исходный контакт не удаляется,
поэтому разъединение возвращает ровно то, что переехало.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from chatballs.conversations.models import ConnectionIdentity, Contact, ContactMerge, Conversation
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event

# Поля карточки, которые дозаполняются из исходного контакта, если у целевого
# они пустые. Что именно заполнили — запоминаем, чтобы очистить при разъединении.
CARD_FIELDS = ("name", "phone", "avatar_url", "description", "company", "city")
MIN_REASON_LENGTH = 5


def _clean_reason(reason: str) -> str:
    cleaned = (reason or "").strip()
    if len(cleaned) < MIN_REASON_LENGTH:
        raise ValidationError(t("sales.merge_reason_required"))
    return cleaned[:2000]


@transaction.atomic
def merge_contacts(*, organization, target_id: int, source_id: int, reason: str, actor, request=None) -> ContactMerge:
    """Перенести идентичности и диалоги source в target."""
    cleaned = _clean_reason(reason)
    if target_id == source_id:
        raise ValidationError(t("sales.merge_self"))
    try:
        target = Contact.objects.select_for_update().get(organization=organization, id=target_id)
        source = Contact.objects.select_for_update().get(organization=organization, id=source_id)
    except Contact.DoesNotExist as error:
        raise ValidationError(t("sales.contact_not_found")) from error
    if source.merged_into_id is not None or target.merged_into_id is not None:
        raise ValidationError(t("sales.already_merged"))

    identity_ids = list(ConnectionIdentity.objects.filter(contact=source).values_list("id", flat=True))
    conversation_ids = list(
        Conversation.objects.filter(organization=organization, contact=source).values_list("id", flat=True)
    )
    ConnectionIdentity.objects.filter(id__in=identity_ids).update(contact=target)
    Conversation.objects.filter(id__in=conversation_ids).update(contact=target)

    filled: list[str] = []
    for field in CARD_FIELDS:
        if not getattr(target, field) and getattr(source, field):
            setattr(target, field, getattr(source, field))
            filled.append(field)
    if filled:
        target.save(update_fields=filled)

    source.merged_into = target
    source.save(update_fields=["merged_into"])

    merge = ContactMerge.objects.create(
        organization=organization,
        target=target,
        source=source,
        reason=cleaned,
        actor=actor,
        moved_identity_ids=identity_ids,
        moved_conversation_ids=conversation_ids,
        filled_fields=filled,
    )
    record_audit_event(
        action="contacts.merged",
        actor=actor,
        organization=organization,
        object_type="Contact",
        object_id=str(target.id),
        payload={
            "sourceId": source.id,
            "reason": cleaned,
            "identities": len(identity_ids),
            "conversations": len(conversation_ids),
        },
        request=request,
    )
    return merge


@transaction.atomic
def revert_merge(*, organization, merge_id: int, reason: str, actor, request=None) -> ContactMerge:
    """Вернуть перенесённые идентичности и диалоги исходному контакту."""
    cleaned = _clean_reason(reason)
    try:
        merge = ContactMerge.objects.select_for_update().get(organization=organization, id=merge_id)
    except ContactMerge.DoesNotExist as error:
        raise ValidationError(t("sales.merge_not_found")) from error
    if merge.reverted_at is not None:
        raise ValidationError(t("sales.already_unmerged"))

    source = merge.source
    target = merge.target
    ConnectionIdentity.objects.filter(id__in=merge.moved_identity_ids).update(contact=source)
    Conversation.objects.filter(id__in=merge.moved_conversation_ids).update(contact=source)
    if merge.filled_fields:
        for field in merge.filled_fields:
            setattr(target, field, "")
        target.save(update_fields=list(merge.filled_fields))

    source.merged_into = None
    source.save(update_fields=["merged_into"])

    merge.reverted_at = timezone.now()
    merge.reverted_by = actor
    merge.revert_reason = cleaned
    merge.save(update_fields=["reverted_at", "reverted_by", "revert_reason"])

    record_audit_event(
        action="contacts.unmerged",
        actor=actor,
        organization=organization,
        object_type="Contact",
        object_id=str(target.id),
        payload={"sourceId": source.id, "reason": cleaned, "mergeId": merge.id},
        request=request,
    )
    return merge
