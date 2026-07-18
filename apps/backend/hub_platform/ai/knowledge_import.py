from dataclasses import dataclass, field

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from hub_platform.ai.knowledge_conflicts import KnowledgeScopeConflict
from hub_platform.ai.knowledge_policy import (
    employee_can_write_knowledge,
    require_knowledge_create,
)
from hub_platform.ai.knowledge_services import (
    KnowledgeInput,
    create_knowledge,
    update_knowledge,
)
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.knowledge_visibility import departments_for_scope
from hub_platform.ai.models import Knowledge, KnowledgeCategory
from hub_platform.identity.models import Department, DepartmentStatus
from hub_platform.tenancy.context import TenantContext


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
        raise ValidationError({"title": "Title is required"})
    return value.strip()


def _content(document: dict[str, object]) -> str:
    value = document.get("content")
    if not isinstance(value, str):
        raise ValidationError({"content": "Content string is required"})
    return value


def _description(document: dict[str, object], *, default: str) -> str:
    if "description" not in document:
        return default
    value = document["description"]
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError({"description": "Description must be a string"})
    return value.strip()


def _category_for_path(*, context: TenantContext, raw_path: object) -> KnowledgeCategory:
    if not isinstance(raw_path, list) or not raw_path:
        raise ValidationError({"categoryPath": "Non-empty category path required"})
    parent_id = None
    category = None
    for raw_name in raw_path:
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValidationError({"categoryPath": "Category names must be non-empty strings"})
        try:
            category = KnowledgeCategory.objects.get(
                organization_id=context.organization_id,
                parent_id=parent_id,
                name=raw_name.strip(),
            )
        except KnowledgeCategory.DoesNotExist as error:
            raise ValidationError({"categoryPath": "Category path not found"}) from error
        parent_id = category.id
    assert category is not None
    return category


def _visibility(document: dict[str, object], *, default: str) -> str:
    if "visibility" not in document:
        return default
    value = document["visibility"]
    if not isinstance(value, str) or value not in KnowledgeVisibility.values:
        raise ValidationError({"visibility": "Unknown knowledge visibility"})
    return value


def _departments_for_codes(*, context: TenantContext, raw_codes: object) -> list[Department]:
    if not isinstance(raw_codes, list):
        raise ValidationError({"departmentCodes": "List of department codes required"})
    codes: list[str] = []
    for raw_code in raw_codes:
        if not isinstance(raw_code, str) or not raw_code.strip():
            raise ValidationError({"departmentCodes": "Department codes must be strings"})
        code = raw_code.strip()
        if code not in codes:
            codes.append(code)
    departments = list(
        Department.objects.filter(
            organization_id=context.organization_id,
            status=DepartmentStatus.ACTIVE,
            code__in=codes,
        )
    )
    if len(departments) != len(codes):
        raise ValidationError({"departmentCodes": "Unknown or disabled department"})
    by_code = {department.code: department for department in departments}
    return [by_code[code] for code in codes]


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
        .prefetch_related("department_links")
        .first()
    )
    explicit_category = "categoryPath" in document
    explicit_visibility = "visibility" in document
    explicit_departments = "departmentCodes" in document
    category = (
        _category_for_path(context=context, raw_path=document["categoryPath"])
        if explicit_category
        else None
    )

    if existing is None:
        visibility = _visibility(
            document,
            default=KnowledgeVisibility.ORGANIZATION,
        )
        departments = (
            _departments_for_codes(
                context=context,
                raw_codes=document["departmentCodes"],
            )
            if explicit_departments
            else []
        )
        departments_for_scope(
            context=context,
            visibility=visibility,
            department_ids=[department.id for department in departments],
        )
        require_knowledge_create(
            context=context,
            visibility=visibility,
            department_ids=[department.id for department in departments],
        )
        create_knowledge(
            context=context,
            data=KnowledgeInput(
                title=title,
                description=_description(document, default=""),
                content=content,
                is_enabled=True,
                category_id=category.id if category is not None else None,
                visibility=visibility,
                department_ids=tuple(department.id for department in departments),
            ),
        )
        return "created"

    current_department_ids = list(existing.department_links.values_list("department_id", flat=True))
    visibility = _visibility(document, default=existing.visibility)
    if explicit_departments:
        departments = _departments_for_codes(
            context=context,
            raw_codes=document["departmentCodes"],
        )
        department_ids = [department.id for department in departments]
    elif explicit_visibility and visibility == KnowledgeVisibility.ORGANIZATION:
        department_ids = []
    else:
        department_ids = current_department_ids
    if explicit_visibility or explicit_departments:
        departments_for_scope(
            context=context,
            visibility=visibility,
            department_ids=department_ids,
        )
    if not employee_can_write_knowledge(
        context=context,
        knowledge=existing,
        visibility=visibility,
        department_ids=department_ids,
    ):
        raise PermissionDenied("Knowledge scope is not manageable")

    description = _description(document, default=existing.description)
    category_id = category.id if category is not None else existing.category_id
    unchanged = (
        existing.description == description
        and existing.content == content
        and existing.category_id == category_id
        and existing.visibility == visibility
        and set(current_department_ids) == set(department_ids)
    )
    if unchanged:
        return "unchanged"
    metadata_scope_explicit = explicit_visibility or explicit_departments
    update_knowledge(
        context=context,
        knowledge=existing,
        data=KnowledgeInput(
            title=title,
            description=description,
            content=content,
            is_enabled=existing.is_enabled,
            category_id=category.id if explicit_category and category is not None else None,
            visibility=visibility if metadata_scope_explicit else None,
            department_ids=tuple(department_ids) if metadata_scope_explicit else None,
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
                raise ValidationError({"document": "Document must be an object"})
            outcome = _import_document(context=context, document=raw_document)
        except ValidationError as error:
            result.failed.append({"title": title, "detail": _validation_detail(error)})
            continue
        except PermissionDenied as error:
            result.failed.append({"title": title, "detail": str(error)})
            continue
        except KnowledgeScopeConflict as error:
            result.failed.append({"title": title, "detail": str(error)})
            continue
        if outcome == "created":
            result.created += 1
        elif outcome == "updated":
            result.updated += 1
        else:
            result.unchanged += 1
    return result
