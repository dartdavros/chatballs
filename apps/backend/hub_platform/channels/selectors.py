from django.db.models import QuerySet

from hub_platform.channels.models import Channel
from hub_platform.tenancy.context import TenantContext


def channels_for_context(context: TenantContext) -> QuerySet[Channel]:
    return (
        Channel.objects.filter(organization_id=context.organization_id)
        .select_related("product", "department", "provider_integration", "ai_agent")
        .order_by("name")
    )


def channel_for_context(*, context: TenantContext, channel_id: int) -> Channel:
    return channels_for_context(context).get(id=channel_id)
