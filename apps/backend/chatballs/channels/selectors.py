from django.db.models import Count, Prefetch, Q, QuerySet

from chatballs.channels.authorization import CHANNELS_VIEW, has_organization_capability
from chatballs.channels.models import Channel
from chatballs.conversations.models import LifecycleState
from chatballs.integrations.models import Integration
from chatballs.tenancy.context import TenantContext


def _with_relations(queryset: QuerySet[Channel]) -> QuerySet[Channel]:
    return queryset.select_related(
        "product", "group", "ai_agent", "ai_agent__provider_integration"
    ).prefetch_related(
        Prefetch("connections", queryset=Integration.objects.order_by("id"))
    ).annotate(
        # Один агрегат на весь список: N+1 запросов на счётчик не допускается
        # (SPEC-HUB-0027 §6.1).
        open_conversations_count=Count(
            "conversations",
            filter=Q(conversations__lifecycle=LifecycleState.OPEN),
            distinct=True,
        )
    )


def channels_in_organization(context: TenantContext) -> QuerySet[Channel]:
    """Все каналы организации, без capability-среза.

    Для потребителей, которые авторизуются собственной capability и лишь
    используют канал как измерение (обзор диалогов). Публичное API каналов
    ходит через `channels_for_context`.
    """
    return (
        Channel.objects.filter(organization_id=context.organization_id)
        .select_related("product", "group", "ai_agent", "ai_agent__provider_integration")
        .order_by("name")
    )


def channels_for_context(
    context: TenantContext, *, capability: str = CHANNELS_VIEW
) -> QuerySet[Channel]:
    """Каналы организации, видимые актору: доступ ролевой (SPEC-HUB-0031 §3),
    у EMPLOYEE нет channels.view — список пуст."""
    queryset = _with_relations(
        Channel.objects.filter(organization_id=context.organization_id)
    ).order_by("name")
    if has_organization_capability(context, capability):
        return queryset
    return queryset.none()


def channel_for_context(
    *, context: TenantContext, channel_id: int, capability: str = CHANNELS_VIEW
) -> Channel:
    return channels_for_context(context, capability=capability).get(id=channel_id)
