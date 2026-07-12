"""Аналитика продаж по подтверждённым фактам (SPEC-HUB-0014 §9).

В production-выручку входят только PRODUCTION-записи со статусами CONFIRMED и
PARTIALLY_REFUNDED с учётом возврата. REFUNDED даёт нулевую чистую выручку.
CANCELLED, LOCAL и STAGING в действующую выручку не входят.
"""

from __future__ import annotations

from django.db.models import Count, F, Sum
from django.db.models.functions import Coalesce

from hub_platform.sales.models import Environment, ProcessingStatus, Sale, SaleEvent, SaleStatus

# Статусы, формирующие действующую выручку.
_REVENUE_STATUSES = (SaleStatus.CONFIRMED, SaleStatus.PARTIALLY_REFUNDED)


def _net_expr():
    return F("amount_minor") - F("refunded_amount_minor")


def sales_analytics(organization_id: int, *, date_from=None, date_to=None) -> dict[str, object]:
    base = Sale.objects.filter(organization_id=organization_id, environment=Environment.PRODUCTION)
    if date_from:
        base = base.filter(occurred_at__gte=date_from)
    if date_to:
        base = base.filter(occurred_at__lte=date_to)

    revenue_qs = base.filter(status__in=_REVENUE_STATUSES)

    # Ключи агрегатов НЕ должны совпадать с именами полей модели: иначе алиас
    # затеняет поле внутри Sum(_net_expr()) и Django падает с FieldError.
    totals = revenue_qs.aggregate(
        gross_count=Count("id"),
        gross_revenue=Coalesce(Sum("amount_minor"), 0),
        refunded_total=Coalesce(Sum("refunded_amount_minor"), 0),
        net_revenue=Coalesce(Sum(_net_expr()), 0),
    )
    cancelled_count = base.filter(status=SaleStatus.CANCELLED).count()
    refunded_count = base.filter(status=SaleStatus.REFUNDED).count()

    by_product = list(
        revenue_qs.values("product__code", "product__name")
        .annotate(count=Count("id"), netMinor=Coalesce(Sum(_net_expr()), 0))
        .order_by("-netMinor")
    )
    by_channel = list(
        revenue_qs.values("conversation__channel__code", "conversation__channel__name")
        .annotate(count=Count("id"), netMinor=Coalesce(Sum(_net_expr()), 0))
        .order_by("-netMinor")
    )
    by_actor = list(
        revenue_qs.values("attributed_actor_type", "attributed_actor_id")
        .annotate(count=Count("id"), netMinor=Coalesce(Sum(_net_expr()), 0))
        .order_by("-netMinor")
    )
    by_attribution = list(
        revenue_qs.values("attribution_method")
        .annotate(count=Count("id"), netMinor=Coalesce(Sum(_net_expr()), 0))
        .order_by("-count")
    )

    unattributed = revenue_qs.filter(attribution_method="NONE").count()
    manual = revenue_qs.filter(source_type="MANUAL").count()
    total_for_share = totals["gross_count"] or 0

    # Повторные продажи: клиенты с более чем одной продажей в периоде.
    repeat_customers = (
        revenue_qs.exclude(external_customer_id="")
        .values("product_id", "external_customer_id")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .count()
    )

    event_errors = SaleEvent.objects.filter(
        organization_id=organization_id, processing_status=ProcessingStatus.REJECTED
    ).count()

    return {
        "grossSalesCount": totals["gross_count"],
        "grossRevenueMinor": totals["gross_revenue"],
        "refundedAmountMinor": totals["refunded_total"],
        "netRevenueMinor": totals["net_revenue"],
        "cancelledSalesCount": cancelled_count,
        "refundedSalesCount": refunded_count,
        "salesByProduct": by_product,
        "salesByChannel": by_channel,
        "salesByActor": by_actor,
        "salesByAttributionMethod": by_attribution,
        "repeatCustomerSales": repeat_customers,
        "unattributedSales": unattributed,
        "manualSalesShare": round(manual / total_for_share, 4) if total_for_share else 0.0,
        "integrationEventErrors": event_errors,
    }
