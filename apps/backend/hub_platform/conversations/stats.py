"""Real sales-department overview aggregates (no fabricated numbers).

Hub has no commerce/orders domain yet, so sales/revenue/conversion are not
computable and are intentionally omitted — the UI shows them as "—". Everything
here is derived from real conversations, messages and LLM usage.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone

from hub_platform.ai.models import LlmInvocation
from hub_platform.channels.selectors import channels_in_organization
from hub_platform.conversations.models import (
    Conversation,
    ControlMode,
    ExpectedResponder,
    LifecycleState,
    Message,
)
from hub_platform.orders.models import Order, PaymentStatus

_ACTIVE_WINDOW = timedelta(minutes=15)
_WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _window(period: str, now: datetime) -> tuple[datetime, datetime]:
    if period == "d7":
        start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "d30":
        start = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    span = now - start
    return start, start - span


def _chart(
    org_id: int,
    period: str,
    start: datetime,
    now: datetime,
    department_ids: set[int] | None,
) -> dict:
    qs = Conversation.objects.filter(organization_id=org_id, created_at__gte=start)
    if department_ids is not None:
        qs = qs.filter(channel__department_id__in=department_ids)
    if period == "today":
        rows = qs.annotate(b=TruncHour("created_at")).values("b").annotate(c=Count("id"))
        counts = {row["b"].astimezone(now.tzinfo).hour: row["c"] for row in rows}
        hours = list(range(start.hour, now.hour + 1)) or [now.hour]
        values = [counts.get(hour, 0) for hour in hours]
        labels = [f"{hour:02d}" for hour in hours]
    else:
        rows = qs.annotate(b=TruncDate("created_at")).values("b").annotate(c=Count("id"))
        counts = {row["b"]: row["c"] for row in rows}
        days = (now.date() - start.date()).days + 1
        dates = [start.date() + timedelta(days=offset) for offset in range(days)]
        values = [counts.get(day, 0) for day in dates]
        if period == "d7":
            labels = [_WEEKDAYS[day.weekday()] for day in dates]
        else:
            labels = [str(day.day) if index % 5 == 0 else "" for index, day in enumerate(dates)]
    return {"values": values, "labels": labels}


def _ai_cost(
    org_id: int,
    start: datetime,
    end: datetime | None = None,
    department_ids: set[int] | None = None,
) -> int:
    qs = LlmInvocation.objects.filter(channel__organization_id=org_id, created_at__gte=start)
    if department_ids is not None:
        qs = qs.filter(channel__department_id__in=department_ids)
    if end is not None:
        qs = qs.filter(created_at__lt=end)
    return qs.aggregate(total=Sum("cost_micros"))["total"] or 0


def sales_overview_stats(
    context,
    period: str,
    department_ids: set[int] | None = None,
) -> dict:
    organization_id = context.organization_id
    now = timezone.now()
    start, prev_start = _window(period, now)

    open_qs = Conversation.objects.filter(organization_id=organization_id, lifecycle=LifecycleState.OPEN)
    if department_ids is not None:
        open_qs = open_qs.filter(channel__department_id__in=department_ids)
    open_dialogs = open_qs.count()
    # «Ждут оператора» = очередь: диалоги, которые никто не взял (PAUSED).
    # Взятые оператором (HUMAN), но ещё без ответа, очередью не считаются —
    # иначе бейдж «Диалоги» показывает число при полностью разобранном inbox.
    waiting = open_qs.filter(control_mode=ControlMode.PAUSED).count()
    ops = {
        "openDialogs": open_dialogs,
        "activeNow": open_qs.filter(last_activity_at__gte=now - _ACTIVE_WINDOW).count(),
        "onAI": open_qs.filter(control_mode=ControlMode.AI).count(),
        "onOperators": open_qs.filter(control_mode=ControlMode.HUMAN).count(),
        "waiting": waiting,
    }

    period_qs = Conversation.objects.filter(organization_id=organization_id, created_at__gte=start)
    if department_ids is not None:
        period_qs = period_qs.filter(channel__department_id__in=department_ids)
    dialogs = period_qs.count()
    paid = Order.objects.filter(organization_id=organization_id, payment_status=PaymentStatus.PAID)
    if department_ids is not None:
        paid = paid.filter(conversation__channel__department_id__in=department_ids)
    period_paid = paid.filter(paid_at__gte=start)
    prev_paid = paid.filter(paid_at__gte=prev_start, paid_at__lt=start)
    sales = period_paid.count()
    revenue = period_paid.aggregate(total=Sum("amount_minor"))["total"] or 0
    period_block = {
        "dialogs": dialogs,
        "dialogsPrev": Conversation.objects.filter(
            organization_id=organization_id, created_at__gte=prev_start, created_at__lt=start
        ).filter(
            **(
                {"channel__department_id__in": department_ids}
                if department_ids is not None
                else {}
            )
        ).count(),
        "messages": Message.objects.filter(
            conversation__organization_id=organization_id,
            created_at__gte=start,
        ).filter(
            **(
                {"conversation__channel__department_id__in": department_ids}
                if department_ids is not None
                else {}
            )
        ).count(),
        "aiCostMicros": _ai_cost(organization_id, start, department_ids=department_ids),
        "aiCostPrevMicros": _ai_cost(
            organization_id, prev_start, start, department_ids=department_ids
        ),
        "sales": sales,
        "salesPrev": prev_paid.count(),
        "revenueMinor": revenue,
        "revenuePrevMinor": prev_paid.aggregate(total=Sum("amount_minor"))["total"] or 0,
        # Конверсия: оплаченные заказы к новым диалогам периода.
        "conversion": round(sales / dialogs * 100, 1) if dialogs else 0.0,
    }

    open_by_channel = dict(open_qs.values_list("channel_id").annotate(c=Count("id")))
    period_by_channel = dict(period_qs.values_list("channel_id").annotate(c=Count("id")))
    sales_by_product = {row["product_id"]: row for row in period_paid.values("product_id").annotate(n=Count("id"), revenue=Sum("amount_minor"))}

    by_channel: list[dict] = []
    by_product: dict[str, dict] = {}
    channels = channels_in_organization(context)
    if department_ids is not None:
        channels = channels.filter(department_id__in=department_ids)
    for channel in channels:
        open_count = open_by_channel.get(channel.id, 0)
        period_count = period_by_channel.get(channel.id, 0)
        by_channel.append({"code": channel.code, "name": channel.name, "openDialogs": open_count, "dialogs": period_count})
        if channel.product_id:
            bucket = by_product.setdefault(
                channel.product.code,
                {"code": channel.product.code, "name": channel.product.name, "openDialogs": 0, "dialogs": 0, "sales": 0, "revenueMinor": 0},
            )
            bucket["openDialogs"] += open_count
            bucket["dialogs"] += period_count
            row = sales_by_product.pop(channel.product_id, None)  # учитываем продажи продукта один раз
            if row:
                bucket["sales"] += row["n"]
                bucket["revenueMinor"] += row["revenue"] or 0

    problems = []
    for conversation in (
        open_qs.filter(expected_responder=ExpectedResponder.OPERATOR)
        .select_related("contact", "support_identity_snapshot", "channel", "channel__product")
        .order_by("last_activity_at")[:5]
    ):
        minutes = int((now - conversation.last_activity_at).total_seconds() // 60)
        meta = conversation.channel.name
        # Имя клиента: sales Contact.name либо display_name support-снапшота.
        snapshot = conversation.support_identity_snapshot
        if conversation.contact_id:
            title = conversation.contact.name or "Гость"
        elif snapshot is not None:
            title = snapshot.display_name or f"client:{snapshot.subject_key[:8]}"
        else:
            title = "Гость"
        problems.append(
            {
                "conversationId": conversation.id,
                "title": title,
                "meta": meta,
                "minutes": minutes,
            }
        )

    return {
        "waiting": waiting,  # обратная совместимость с бейджем сайдбара
        "ops": ops,
        "period": period_block,
        "byChannel": by_channel,
        "byProduct": list(by_product.values()),
        "chart": _chart(organization_id, period, start, now, department_ids),
        "problems": problems,
    }
