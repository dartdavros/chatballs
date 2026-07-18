from __future__ import annotations

from collections.abc import Iterable

from django.core.exceptions import PermissionDenied
from django.db.models import Exists, OuterRef, Q, QuerySet

from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.models import AIAgent, Knowledge, KnowledgeDepartment
from hub_platform.identity.policy import (
    ResourceScope,
    accessible_department_ids,
    authorize,
)
from hub_platform.tenancy.context import TenantContext


AI_VIEW = "ai.view"
AI_MANAGE = "ai.manage"


def _department_ids(context: TenantContext, capability: str) -> set[int] | None:
    membership = context.membership
    if membership is None or membership.organization_id != context.organization_id:
        return set()
    return accessible_department_ids(membership, capability)


def readable_knowledge(
    *,
    context: TenantContext,
    queryset: QuerySet[Knowledge],
    capability: str = AI_VIEW,
) -> QuerySet[Knowledge]:
    """Apply employee knowledge visibility before detail, aggregation or paging."""
    queryset = queryset.filter(organization_id=context.organization_id)
    department_ids = _department_ids(context, capability)
    if department_ids is None:
        return queryset
    if not department_ids:
        return queryset.none()
    return queryset.filter(
        Q(visibility=KnowledgeVisibility.ORGANIZATION)
        | Q(
            visibility=KnowledgeVisibility.DEPARTMENTS,
            department_links__department_id__in=department_ids,
        )
    ).distinct()


def writable_knowledge(
    *, context: TenantContext, queryset: QuerySet[Knowledge]
) -> QuerySet[Knowledge]:
    """Return items whose complete current scope is covered by the employee."""
    queryset = queryset.filter(organization_id=context.organization_id)
    department_ids = _department_ids(context, AI_MANAGE)
    if department_ids is None:
        return queryset
    if not department_ids:
        return queryset.none()
    covered_links = KnowledgeDepartment.objects.filter(
        knowledge_id=OuterRef("pk"), department_id__in=department_ids
    )
    uncovered_links = KnowledgeDepartment.objects.filter(
        knowledge_id=OuterRef("pk")
    ).exclude(department_id__in=department_ids)
    return queryset.filter(
        visibility=KnowledgeVisibility.DEPARTMENTS
    ).filter(Exists(covered_links), ~Exists(uncovered_links))


def employee_can_read_knowledge(
    *, context: TenantContext, knowledge: Knowledge
) -> bool:
    if knowledge.organization_id != context.organization_id:
        return False
    return readable_knowledge(
        context=context,
        queryset=Knowledge.objects.filter(pk=knowledge.pk),
    ).exists()


def employee_can_write_knowledge(
    *,
    context: TenantContext,
    knowledge: Knowledge,
    visibility: str | None = None,
    department_ids: Iterable[int] | None = None,
) -> bool:
    """Require full coverage of both the current and proposed knowledge scope."""
    if knowledge.organization_id != context.organization_id:
        return False
    target_visibility = visibility or knowledge.visibility
    target_department_ids = (
        set(department_ids)
        if department_ids is not None
        else set(knowledge.department_links.values_list("department_id", flat=True))
    )
    allowed_ids = _department_ids(context, AI_MANAGE)
    if allowed_ids is None:
        return True
    if knowledge.visibility == KnowledgeVisibility.ORGANIZATION:
        return False
    if target_visibility == KnowledgeVisibility.ORGANIZATION:
        return False
    current_ids = set(
        knowledge.department_links.values_list("department_id", flat=True)
    )
    return bool(current_ids | target_department_ids) and (
        current_ids | target_department_ids
    ).issubset(allowed_ids)


def employee_can_create_knowledge(
    *, context: TenantContext, visibility: str, department_ids: Iterable[int]
) -> bool:
    allowed_ids = _department_ids(context, AI_MANAGE)
    if allowed_ids is None:
        return True
    if visibility != KnowledgeVisibility.DEPARTMENTS:
        return False
    target_ids = set(department_ids)
    return bool(target_ids) and target_ids.issubset(allowed_ids)


def employee_can_manage_categories(*, context: TenantContext) -> bool:
    membership = context.membership
    return membership is not None and authorize(
        membership,
        AI_MANAGE,
        ResourceScope(organization_id=context.organization_id),
    )


def require_knowledge_create(
    *, context: TenantContext, visibility: str, department_ids: Iterable[int]
) -> None:
    if not employee_can_create_knowledge(
        context=context,
        visibility=visibility,
        department_ids=department_ids,
    ):
        raise PermissionDenied("Knowledge scope is not manageable")


def knowledge_is_available_to_agent(
    *, knowledge: Knowledge, agent: AIAgent
) -> bool:
    channel = agent.channel
    if knowledge.organization_id != channel.organization_id:
        return False
    if knowledge.visibility == KnowledgeVisibility.ORGANIZATION:
        return True
    return channel.department_id is not None and knowledge.department_links.filter(
        department_id=channel.department_id
    ).exists()
