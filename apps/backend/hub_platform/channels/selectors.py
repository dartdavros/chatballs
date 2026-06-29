from django.db.models import QuerySet

from hub_platform.channels.models import Channel


def channels_for_organization(organization_id: int) -> QuerySet[Channel]:
    return (
        Channel.objects.filter(organization_id=organization_id)
        .select_related("product", "department", "provider_integration", "ai_agent")
        .order_by("name")
    )


def channel_for_organization(*, organization_id: int, channel_id: int) -> Channel:
    return channels_for_organization(organization_id).get(id=channel_id)
