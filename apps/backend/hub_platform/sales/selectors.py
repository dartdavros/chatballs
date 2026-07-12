from __future__ import annotations

from django.db.models import QuerySet

from hub_platform.sales.models import Environment, Sale, SaleEvent


def sales_for_organization(organization_id: int) -> QuerySet[Sale]:
    return (
        Sale.objects.filter(organization_id=organization_id)
        .select_related("product", "contact", "conversation", "sales_source", "last_event")
        .order_by("-occurred_at")
    )


def sale_for_organization(*, organization_id: int, sale_id: int) -> Sale:
    return sales_for_organization(organization_id).get(id=sale_id)


def events_for_sale(sale: Sale) -> QuerySet[SaleEvent]:
    return sale.events.select_related("actor_user").order_by("received_at", "id")


def apply_sale_filters(qs: QuerySet[Sale], params) -> QuerySet[Sale]:
    """Фильтры реестра продаж (SPEC §8.1)."""
    status = params.get("status")
    if status:
        qs = qs.filter(status=status)
    product = params.get("product")
    if product:
        qs = qs.filter(product_id=product)
    source_type = params.get("sourceType")
    if source_type:
        qs = qs.filter(source_type=source_type)
    environment = params.get("environment")
    if environment:
        qs = qs.filter(environment=environment)
    else:
        # По умолчанию скрываем LOCAL/STAGING из основного реестра (диагностика — по фильтру).
        qs = qs.filter(environment=Environment.PRODUCTION)
    channel = params.get("channel")
    if channel:
        qs = qs.filter(conversation__channel_id=channel)
    contact = params.get("contact")
    if contact:
        qs = qs.filter(contact_id=contact)
    conversation = params.get("conversation")
    if conversation:
        qs = qs.filter(conversation_id=conversation)
    actor = params.get("actor")
    if actor:
        qs = qs.filter(attributed_actor_id=actor)
    attribution = params.get("attribution")
    if attribution == "with":
        qs = qs.exclude(attribution_method="NONE")
    elif attribution == "without":
        qs = qs.filter(attribution_method="NONE")
    date_from = params.get("from")
    if date_from:
        qs = qs.filter(occurred_at__gte=date_from)
    date_to = params.get("to")
    if date_to:
        qs = qs.filter(occurred_at__lte=date_to)
    return qs


def sale_events_with_errors(organization_id: int) -> QuerySet[SaleEvent]:
    return SaleEvent.objects.filter(organization_id=organization_id).exclude(processing_error="")
