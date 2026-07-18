from collections.abc import Iterable
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from hub_platform.ai.agent_knowledge import knowledge_available_to_channel
from hub_platform.ai.knowledge_conflicts import (
    KnowledgeScopeConflict,
    knowledge_scope_conflicts,
)
from hub_platform.ai.knowledge_policy import employee_can_write_knowledge
from hub_platform.ai.knowledge_visibility import departments_for_scope
from hub_platform.ai.models import (
    AIAgent,
    Knowledge,
    KnowledgeCategory,
    KnowledgeDepartment,
)
from hub_platform.ai.services import knowledge_for_agent_ids
from hub_platform.channels.models import Channel
from hub_platform.tenancy.context import TenantContext


def _normalized_knowledge_ids(knowledge_ids: Iterable[int]) -> list[int]:
    normalized: list[int] = []
    for knowledge_id in knowledge_ids:
        if isinstance(knowledge_id, bool) or not isinstance(knowledge_id, int):
            raise ValidationError({"knowledgeIds": "Knowledge IDs must be integers"})
        if knowledge_id not in normalized:
            normalized.append(knowledge_id)
    if not normalized:
        raise ValidationError({"knowledgeIds": "At least one knowledge ID is required"})
    return normalized


def _locked_knowledge(*, context: TenantContext, knowledge_ids: Iterable[int]) -> list[Knowledge]:
    normalized_ids = _normalized_knowledge_ids(knowledge_ids)
    items = list(
        Knowledge.objects.select_for_update()
        .filter(
            organization_id=context.organization_id,
            id__in=normalized_ids,
        )
        .prefetch_related("department_links")
        .order_by("id")
    )
    if len(items) != len(normalized_ids):
        raise ValidationError({"knowledgeIds": "Unknown knowledge item"})
    return items


def _require_bulk_write(
    *,
    context: TenantContext,
    items: Iterable[Knowledge],
    visibility: str | None = None,
    department_ids: Iterable[int] | None = None,
) -> None:
    for knowledge in items:
        if not employee_can_write_knowledge(
            context=context,
            knowledge=knowledge,
            visibility=visibility,
            department_ids=department_ids,
        ):
            raise PermissionDenied("Knowledge scope is not manageable")


@transaction.atomic
def bulk_move_knowledge(
    *, context: TenantContext, knowledge_ids: Iterable[int], category_id: int
) -> list[int]:
    try:
        category = KnowledgeCategory.objects.select_for_update().get(
            id=category_id,
            organization_id=context.organization_id,
        )
    except KnowledgeCategory.DoesNotExist as error:
        raise ValidationError({"categoryId": "Category not found"}) from error
    items = _locked_knowledge(context=context, knowledge_ids=knowledge_ids)
    _require_bulk_write(context=context, items=items)
    now = timezone.now()
    Knowledge.objects.filter(id__in=[item.id for item in items]).update(
        category=category,
        updated_at=now,
    )
    return [item.id for item in items]


@transaction.atomic
def bulk_replace_knowledge_visibility(
    *,
    context: TenantContext,
    knowledge_ids: Iterable[int],
    visibility: str,
    department_ids: Iterable[int],
) -> list[int]:
    departments = departments_for_scope(
        context=context,
        visibility=visibility,
        department_ids=department_ids,
    )
    target_department_ids = [department.id for department in departments]
    items = _locked_knowledge(context=context, knowledge_ids=knowledge_ids)
    _require_bulk_write(
        context=context,
        items=items,
        visibility=visibility,
        department_ids=target_department_ids,
    )
    conflicts = tuple(
        conflict
        for knowledge in items
        for conflict in knowledge_scope_conflicts(
            knowledge=knowledge,
            visibility=visibility,
            department_ids=target_department_ids,
        )
    )
    if conflicts:
        raise KnowledgeScopeConflict(conflicts)

    item_ids = [item.id for item in items]
    Knowledge.objects.filter(id__in=item_ids).update(
        visibility=visibility,
        updated_at=timezone.now(),
    )
    KnowledgeDepartment.objects.filter(knowledge_id__in=item_ids).delete()
    KnowledgeDepartment.objects.bulk_create(
        [
            KnowledgeDepartment(
                organization=context.organization,
                knowledge=knowledge,
                department=department,
            )
            for knowledge in items
            for department in departments
        ]
    )
    return item_ids


@dataclass(frozen=True, slots=True)
class CategorySelectionResult:
    agent: AIAgent
    selected_ids: tuple[int, ...]
    added_ids: tuple[int, ...]


@transaction.atomic
def add_category_knowledge_to_agent(
    *, context: TenantContext, agent: AIAgent, category_id: int
) -> CategorySelectionResult:
    if agent.channel.organization_id != context.organization_id:
        raise ValidationError({"agent": "Agent belongs to another organization"})
    channel = Channel.objects.select_for_update().get(
        id=agent.channel_id,
        organization_id=context.organization_id,
    )
    if not KnowledgeCategory.objects.filter(
        id=category_id,
        organization_id=context.organization_id,
    ).exists():
        raise ValidationError({"categoryId": "Category not found"})

    current_ids = set(agent.knowledge_items.values_list("id", flat=True))
    category_ids = set(
        knowledge_available_to_channel(
            Knowledge.objects.filter(category_id=category_id),
            channel=channel,
        ).values_list("id", flat=True)
    )
    selected_ids = sorted(current_ids | category_ids)
    selected_items = knowledge_for_agent_ids(
        context=context,
        channel=channel,
        knowledge_ids=selected_ids,
    )
    locked = AIAgent.objects.select_for_update().get(id=agent.id, channel=channel)
    locked.knowledge_items.set(selected_items)
    return CategorySelectionResult(
        agent=locked,
        selected_ids=tuple(selected_ids),
        added_ids=tuple(sorted(category_ids - current_ids)),
    )
