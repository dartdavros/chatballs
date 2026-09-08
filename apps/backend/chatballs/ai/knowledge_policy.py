from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet

from chatballs.identity.policy import has_capability_any_scope
from chatballs.ai.models import AIAgent, Knowledge
from chatballs.tenancy.context import TenantContext

AI_VIEW = "ai.view"
AI_MANAGE = "ai.manage"

# Библиотека знаний — общая для организации (ADR-CHATBALLS-0041 §8): областей
# видимости нет, доступ определяется ролью (ai.view/ai.manage у OWNER/ADMIN).


def _has(context: TenantContext, capability: str) -> bool:
    membership = context.membership
    if membership is None or membership.organization_id != context.organization_id:
        return False
    return has_capability_any_scope(membership, capability)


def readable_knowledge(
    *,
    context: TenantContext,
    queryset: QuerySet[Knowledge],
    capability: str = AI_VIEW,
) -> QuerySet[Knowledge]:
    queryset = queryset.filter(organization_id=context.organization_id)
    if _has(context, capability):
        return queryset
    return queryset.none()


def writable_knowledge(
    *, context: TenantContext, queryset: QuerySet[Knowledge]
) -> QuerySet[Knowledge]:
    queryset = queryset.filter(organization_id=context.organization_id)
    if _has(context, AI_MANAGE):
        return queryset
    return queryset.none()


def employee_can_read_knowledge(*, context: TenantContext, knowledge: Knowledge) -> bool:
    if knowledge.organization_id != context.organization_id:
        return False
    return _has(context, AI_VIEW)


def employee_can_write_knowledge(*, context: TenantContext, knowledge: Knowledge) -> bool:
    if knowledge.organization_id != context.organization_id:
        return False
    return _has(context, AI_MANAGE)


def employee_can_manage_categories(*, context: TenantContext) -> bool:
    return _has(context, AI_MANAGE)


def require_knowledge_create(*, context: TenantContext) -> None:
    if not _has(context, AI_MANAGE):
        raise PermissionDenied("ai.manage is required")


def require_category_manage(*, context: TenantContext) -> None:
    if not employee_can_manage_categories(context=context):
        raise PermissionDenied("ai.manage is required")


def knowledge_is_available_to_agent(*, knowledge: Knowledge, agent: AIAgent) -> bool:
    return (
        knowledge.organization_id == agent.organization_id
    )
