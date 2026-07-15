from django.db.models import Count, QuerySet

from hub_platform.ai.models import AIAgent, Knowledge
from hub_platform.tenancy.context import TenantContext


def agents_for_context(context: TenantContext) -> QuerySet[AIAgent]:
    return (
        AIAgent.objects.select_related("channel", "channel__product")
        .prefetch_related("knowledge_items")
        .filter(channel__organization_id=context.organization_id)
        .order_by("channel__name")
    )


def agent_for_context(*, context: TenantContext, agent_id: int) -> AIAgent:
    return agents_for_context(context).get(id=agent_id)


def knowledge_for_context(context: TenantContext) -> QuerySet[Knowledge]:
    return (
        Knowledge.objects.filter(organization_id=context.organization_id)
        .prefetch_related("attachments")
        .annotate(agents_count=Count("agents", distinct=True))
        .order_by("title")
    )


def knowledge_item_for_context(*, context: TenantContext, knowledge_id: int) -> Knowledge:
    return knowledge_for_context(context).get(id=knowledge_id)
