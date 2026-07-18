from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from hub_platform.ai.extraction import extract_text
from hub_platform.ai.indexing import reindex_knowledge
from hub_platform.ai.knowledge_categories import ensure_uncategorized_category
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.knowledge_visibility import replace_knowledge_visibility
from hub_platform.ai.models import (
    Knowledge,
    KnowledgeAttachment,
    KnowledgeCategory,
)
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.storage import adjust_storage_usage
from hub_platform.tenancy.storage_quota import (
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
    visibility: str | None = None
    department_ids: tuple[int, ...] | None = None


def _knowledge_category(*, context: TenantContext, category_id: int | None) -> KnowledgeCategory:
    if category_id is None:
        return ensure_uncategorized_category(context.organization)
    try:
        return KnowledgeCategory.objects.get(
            organization_id=context.organization_id,
            id=category_id,
        )
    except KnowledgeCategory.DoesNotExist as error:
        raise ValidationError({"category": "Category not found"}) from error


@transaction.atomic
def create_knowledge(*, context: TenantContext, data: KnowledgeInput) -> Knowledge:
    if not data.title.strip():
        raise ValidationError({"title": "Title is required"})
    visibility = data.visibility or KnowledgeVisibility.ORGANIZATION
    department_ids = data.department_ids or ()
    knowledge = Knowledge.objects.create(
        organization=context.organization,
        category=_knowledge_category(context=context, category_id=data.category_id),
        title=data.title.strip(),
        description=data.description.strip(),
        content=data.content,
        is_enabled=data.is_enabled,
        visibility=visibility,
    )
    knowledge = replace_knowledge_visibility(
        context=context,
        knowledge=knowledge,
        visibility=visibility,
        department_ids=department_ids,
    )
    reindex_knowledge(knowledge)
    return knowledge


@transaction.atomic
def update_knowledge(
    *, context: TenantContext, knowledge: Knowledge, data: KnowledgeInput
) -> Knowledge:
    if knowledge.organization_id != context.organization_id:
        raise ValidationError({"knowledge": "Knowledge belongs to another organization"})
    if not data.title.strip():
        raise ValidationError({"title": "Title is required"})
    locked = Knowledge.objects.select_for_update().get(pk=knowledge.pk)
    content_changed = locked.content != data.content
    if data.visibility is not None or data.department_ids is not None:
        locked = replace_knowledge_visibility(
            context=context,
            knowledge=locked,
            visibility=data.visibility or locked.visibility,
            department_ids=(
                data.department_ids
                if data.department_ids is not None
                else tuple(locked.department_links.values_list("department_id", flat=True))
            ),
        )
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
        raise ValidationError({"knowledge": "Knowledge belongs to another organization"})
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
        raise ValidationError({"knowledge": "Knowledge belongs to another organization"})
    original_name = (upload.name or "").strip()
    if not original_name:
        raise ValidationError({"file": "File name is required"})
    if upload.size and upload.size > _MAX_ATTACHMENT_BYTES:
        raise ValidationError({"file": "File is too large (max 25 MB)"})
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
        raise ValidationError({"attachment": "Attachment belongs to another organization"})
    knowledge = attachment.knowledge
    released_bytes = attachment.size
    attachment.file.delete(save=False)
    attachment.delete()
    if released_bytes:
        adjust_storage_usage(context=context, delta_bytes=-released_bytes)
    reindex_knowledge(knowledge)
