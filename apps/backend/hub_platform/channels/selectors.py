from django.db.models import Count, Prefetch, Q, QuerySet

from hub_platform.channels.authorization import CHANNELS_VIEW, department_ids_for
from hub_platform.channels.models import Channel
from hub_platform.conversations.models import LifecycleState
from hub_platform.integrations.models import Integration
from hub_platform.tenancy.context import TenantContext


def _with_relations(queryset: QuerySet[Channel]) -> QuerySet[Channel]:
    return queryset.select_related(
        "product", "department", "provider_integration", "ai_agent"
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
        .select_related("product", "department", "provider_integration", "ai_agent")
        .order_by("name")
    )


def channels_for_context(
    context: TenantContext, *, capability: str = CHANNELS_VIEW
) -> QuerySet[Channel]:
    """Каналы организации, видимые актору (SPEC-HUB-0027 §5.2).

    Department-scoped доступ не выдаёт канал без отдела: у такого канала нет
    отдела, который назначение могло бы покрыть.
    """
    queryset = _with_relations(
        Channel.objects.filter(organization_id=context.organization_id)
    ).order_by("name")
    department_ids = department_ids_for(context, capability)
    if department_ids is None:
        return queryset
    return queryset.filter(department_id__in=department_ids)


def channel_for_context(
    *, context: TenantContext, channel_id: int, capability: str = CHANNELS_VIEW
) -> Channel:
    return channels_for_context(context, capability=capability).get(id=channel_id)


def _parse_reference(raw: str) -> tuple[str, int | None]:
    """`none` — явный фильтр «без связи», иначе идентификатор."""
    if raw == "none":
        return "none", None
    try:
        return "id", int(raw)
    except (TypeError, ValueError):
        return "invalid", None


def filter_channels(queryset: QuerySet[Channel], params) -> QuerySet[Channel]:
    """Фильтры §6.2. Scope уже применён селектором и здесь не расширяется."""
    department = params.get("department")
    if department:
        kind, value = _parse_reference(department)
        if kind == "none":
            queryset = queryset.filter(department__isnull=True)
        elif kind == "id":
            queryset = queryset.filter(department_id=value)

    product = params.get("product")
    if product:
        kind, value = _parse_reference(product)
        if kind == "none":
            queryset = queryset.filter(product__isnull=True)
        elif kind == "id":
            queryset = queryset.filter(product_id=value)

    is_active = params.get("isActive")
    if is_active in {"true", "false"}:
        queryset = queryset.filter(is_active=is_active == "true")

    has_agent = params.get("hasAgent")
    if has_agent in {"true", "false"}:
        queryset = queryset.filter(ai_agent__isnull=has_agent == "false")

    search = (params.get("q") or "").strip()
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(code__icontains=search))
    return queryset
