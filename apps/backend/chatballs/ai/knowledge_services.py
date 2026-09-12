from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from chatballs.ai.extraction import extract_text
from chatballs.ai.indexing import reindex_knowledge
from chatballs.ai.knowledge_categories import ensure_uncategorized_category
from chatballs.ai.models import (
    Knowledge,
    KnowledgeAttachment,
    KnowledgeCategory,
)
from chatballs.i18n import t
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.storage import adjust_storage_usage
from chatballs.tenancy.storage_quota import (
    finalize_storage,
    release_storage,
    reserve_storage,
)


@dataclass(frozen=True)
class KnowledgeInput:
    title: str
    description: str
    content: str
    is_enabled: bool
    category_id: int | None = None


def _knowledge_category(*, context: TenantContext, category_id: int | None) -> KnowledgeCategory:
    if category_id is None:
        return ensure_uncategorized_category(context.organization)
    try:
        return KnowledgeCategory.objects.get(
            organization_id=context.organization_id,
            id=category_id,
        )
    except KnowledgeCategory.DoesNotExist as error:
        raise ValidationError({"category": t("ai.category_not_found")}) from error


@transaction.atomic
def create_knowledge(*, context: TenantContext, data: KnowledgeInput) -> Knowledge:
    if not data.title.strip():
        raise ValidationError({"title": t("ai.title_required")})
    knowledge = Knowledge.objects.create(
        organization=context.organization,
        category=_knowledge_category(context=context, category_id=data.category_id),
        title=data.title.strip(),
        description=data.description.strip(),
        content=data.content,
        is_enabled=data.is_enabled,
    )
    reindex_knowledge(knowledge)
    return knowledge


@transaction.atomic
def update_knowledge(
    *, context: TenantContext, knowledge: Knowledge, data: KnowledgeInput
) -> Knowledge:
    if knowledge.organization_id != context.organization_id:
        raise ValidationError({"knowledge": t("ai.knowledge_other_organization")})
    if not data.title.strip():
        raise ValidationError({"title": t("ai.title_required")})
    locked = Knowledge.objects.select_for_update().get(pk=knowledge.pk)
    content_changed = locked.content != data.content
    locked.title = data.title.strip()
    locked.description = data.description.strip()
    locked.content = data.content
    locked.is_enabled = data.is_enabled
    if data.category_id is not None:
        locked.category = _knowledge_category(
            context=context,
            category_id=data.category_id,
        )
    locked.save(
        update_fields=[
            "title",
            "description",
            "content",
            "is_enabled",
            "category",
            "updated_at",
        ]
    )
    if content_changed:
        reindex_knowledge(locked)
    return locked


def delete_knowledge(*, context: TenantContext, knowledge: Knowledge) -> None:
    if knowledge.organization_id != context.organization_id:
        raise ValidationError({"knowledge": t("ai.knowledge_other_organization")})
    attachments = list(knowledge.attachments.all())
    released_bytes = sum(attachment.size for attachment in attachments)
    for attachment in attachments:
        attachment.file.delete(save=False)
    knowledge.delete()
    if released_bytes:
        adjust_storage_usage(context=context, delta_bytes=-released_bytes)


_MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


@transaction.atomic
def add_attachment(
    *, context: TenantContext, knowledge: Knowledge, upload: UploadedFile
) -> KnowledgeAttachment:
    if knowledge.organization_id != context.organization_id:
        raise ValidationError({"knowledge": t("ai.knowledge_other_organization")})
    original_name = (upload.name or "").strip()
    if not original_name:
        raise ValidationError({"file": t("ai.file_name_required")})
    if upload.size and upload.size > _MAX_ATTACHMENT_BYTES:
        raise ValidationError({"file": t("ai.file_too_large_25")})
    existing = knowledge.attachments.filter(original_name=original_name).first()
    existing_size = existing.size if existing is not None else 0
    data = upload.read()
    reservation_key = f"attachment:{knowledge.id}:{original_name}"
    reserve_storage(context=context, expected_bytes=len(data), idempotency_key=reservation_key)
    try:
        if existing is not None:
            existing.file.delete(save=False)
            existing.delete()
            if existing_size:
                adjust_storage_usage(context=context, delta_bytes=-existing_size)
        content_type = upload.content_type or ""
        attachment = KnowledgeAttachment(
            organization=context.organization,
            knowledge=knowledge,
            original_name=original_name,
            content_type=content_type,
            size=len(data),
            extracted_text=extract_text(
                filename=original_name, content_type=content_type, data=data
            ),
        )
        from django.core.files.base import ContentFile

        attachment.file.save(original_name, ContentFile(data), save=True)
    except Exception:
        release_storage(context=context, idempotency_key=reservation_key)
        raise
    finalize_storage(context=context, idempotency_key=reservation_key, actual_bytes=len(data))
    reindex_knowledge(knowledge)
    return attachment


def delete_attachment(*, context: TenantContext, attachment: KnowledgeAttachment) -> None:
    if attachment.knowledge.organization_id != context.organization_id:
        raise ValidationError({"attachment": t("ai.attachment_other_organization")})
    knowledge = attachment.knowledge
    released_bytes = attachment.size
    attachment.file.delete(save=False)
    attachment.delete()
    if released_bytes:
        adjust_storage_usage(context=context, delta_bytes=-released_bytes)
    reindex_knowledge(knowledge)
