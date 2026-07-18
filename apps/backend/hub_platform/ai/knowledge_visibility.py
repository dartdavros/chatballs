from collections.abc import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction

from hub_platform.ai.knowledge_conflicts import require_knowledge_scope_compatible
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.models import Knowledge, KnowledgeDepartment
from hub_platform.identity.models import Department, DepartmentStatus
from hub_platform.tenancy.context import TenantContext


def _normalize_department_ids(department_ids: Iterable[int]) -> list[int]:
    normalized: list[int] = []
    for department_id in department_ids:
        if isinstance(department_id, bool) or not isinstance(department_id, int):
            raise ValidationError({"departments": "Department IDs must be integers"})
        if department_id not in normalized:
            normalized.append(department_id)
    return normalized


def _departments_for_scope(
    *, context: TenantContext, visibility: str, department_ids: Iterable[int]
) -> list[Department]:
    if visibility not in KnowledgeVisibility.values:
        raise ValidationError({"visibility": "Unknown knowledge visibility"})

    normalized_ids = _normalize_department_ids(department_ids)
    if visibility == KnowledgeVisibility.ORGANIZATION:
        if normalized_ids:
            raise ValidationError({"departments": "Organization knowledge cannot have departments"})
        return []
    if not normalized_ids:
        raise ValidationError(
            {"departments": "Department knowledge requires at least one department"}
        )

    departments = list(
        Department.objects.select_for_update().filter(
            organization_id=context.organization_id,
            status=DepartmentStatus.ACTIVE,
            id__in=normalized_ids,
        )
    )
    if len(departments) != len(normalized_ids):
        raise ValidationError({"departments": "Unknown or disabled department"})
    by_id = {department.id: department for department in departments}
    return [by_id[department_id] for department_id in normalized_ids]


@transaction.atomic
def replace_knowledge_visibility(
    *,
    context: TenantContext,
    knowledge: Knowledge,
    visibility: str,
    department_ids: Iterable[int],
) -> Knowledge:
    if knowledge.organization_id != context.organization_id:
        raise ValidationError({"knowledge": "Knowledge belongs to another organization"})

    locked = Knowledge.objects.select_for_update().get(pk=knowledge.pk)
    departments = _departments_for_scope(
        context=context,
        visibility=visibility,
        department_ids=department_ids,
    )
    require_knowledge_scope_compatible(
        knowledge=locked,
        visibility=visibility,
        department_ids=[department.id for department in departments],
    )
    locked.visibility = visibility
    locked.save(update_fields=["visibility", "updated_at"])
    locked.department_links.all().delete()
    KnowledgeDepartment.objects.bulk_create(
        [
            KnowledgeDepartment(
                organization=context.organization,
                knowledge=locked,
                department=department,
            )
            for department in departments
        ]
    )
    return locked
