from dataclasses import dataclass, field

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from chatballs.ai.knowledge_policy import (
    employee_can_write_knowledge,
    require_knowledge_create,
)
from chatballs.ai.knowledge_services import (
    KnowledgeInput,
    create_knowledge,
    update_knowledge,
)
from chatballs.ai.models import Knowledge, KnowledgeCategory
from chatballs.i18n import t
from chatballs.tenancy.context import TenantContext


@dataclass(slots=True)
class KnowledgeImportResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: list[dict[str, str]] = field(default_factory=list)

    def payload(self) -> dict[str, object]:
        return {
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "failed": self.failed,
        }


def _title(document: dict[str, object]) -> str:
    value = document.get("title")
    if not isinstance(value, str) or not value.strip():
        raise ValidationError({"title": t("ai.title_required")})
    return value.strip()


def _content(document: dict[str, object]) -> str:
    value = document.get("content")
    if not isinstance(value, str):
        raise ValidationError({"content": t("ai.content_required")})
    return value


def _description(document: dict[str, object], *, default: str) -> str:
    if "description" not in document:
        return default
    value = document["description"]
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError({"description": t("ai.description_string")})
    return value.strip()


def _category_for_path(*, context: TenantContext, raw_path: object) -> KnowledgeCategory:
    if not isinstance(raw_path, list) or not raw_path:
        raise ValidationError({"categoryPath": t("ai.category_path_required")})
    parent_id = None
    category = None
    for raw_name in raw_path:
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValidationError({"categoryPath": t("ai.category_names_strings")})
        try:
            category = KnowledgeCategory.objects.get(
                organization_id=context.organization_id,
                parent_id=parent_id,
                name=raw_name.strip(),
            )
        except KnowledgeCategory.DoesNotExist as error:
            raise ValidationError({"categoryPath": t("ai.category_path_not_found")}) from error
        parent_id = category.id
    assert category is not None
    return category


def _validation_detail(error: ValidationError) -> str:
    if hasattr(error, "message_dict"):
        return "; ".join(
            message for messages in error.message_dict.values() for message in messages
        )
    return "; ".join(error.messages)


@transaction.atomic
def _import_document(*, context: TenantContext, document: dict[str, object]) -> str:
    title = _title(document)
    content = _content(document)
    existing = (
        Knowledge.objects.select_for_update()
        .filter(organization_id=context.organization_id, title=title)
        .first()
    )
    explicit_category = "categoryPath" in document
    category = (
        _category_for_path(context=context, raw_path=document["categoryPath"])
        if explicit_category
        else None
    )

    if existing is None:
        require_knowledge_create(context=context)
        create_knowledge(
            context=context,
            data=KnowledgeInput(
                title=title,
                description=_description(document, default=""),
                content=content,
                is_enabled=True,
                category_id=category.id if category is not None else None,
            ),
        )
        return "created"

    if not employee_can_write_knowledge(context=context, knowledge=existing):
        raise PermissionDenied("Knowledge is not manageable")

    description = _description(document, default=existing.description)
    category_id = category.id if category is not None else existing.category_id
    unchanged = (
        existing.description == description
        and existing.content == content
        and existing.category_id == category_id
    )
    if unchanged:
        return "unchanged"
    update_knowledge(
        context=context,
        knowledge=existing,
        data=KnowledgeInput(
            title=title,
            description=description,
            content=content,
            is_enabled=existing.is_enabled,
            category_id=category.id if explicit_category and category is not None else None,
        ),
    )
    return "updated"


def import_knowledge_documents(
    *, context: TenantContext, documents: list[object]
) -> KnowledgeImportResult:
    result = KnowledgeImportResult()
    for raw_document in documents:
        title = ""
        if isinstance(raw_document, dict):
            raw_title = raw_document.get("title")
            title = raw_title.strip() if isinstance(raw_title, str) else ""
        try:
            if not isinstance(raw_document, dict):
                raise ValidationError({"document": t("ai.document_object_required")})
            outcome = _import_document(context=context, document=raw_document)
        except ValidationError as error:
            result.failed.append({"title": title, "detail": _validation_detail(error)})
            continue
        except PermissionDenied as error:
            result.failed.append({"title": title, "detail": str(error)})
            continue
        if outcome == "created":
            result.created += 1
        elif outcome == "updated":
            result.updated += 1
        else:
            result.unchanged += 1
    return result
