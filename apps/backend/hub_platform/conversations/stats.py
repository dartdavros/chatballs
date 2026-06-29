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
from hub_platform.channels.selectors import channels_for_organization
from hub_platform.conversations.models import (
    Conversation,
    ControlMode,
    ExpectedResponder,
    LifecycleState,
    Message,
)

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


def _chart(org_id: int, period: str, start: datetime, now: datetime) -> dict:
    qs = Conversation.objects.filter(organization_id=org_id, created_at__gte=start)
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


def _ai_cost(org_id: int, start: datetime, end: datetime | None = None) -> int:
    qs = LlmInvocation.objects.filter(channel__organization_id=org_id, created_at__gte=start)
    if end is not None:
        qs = qs.filter(created_at__lt=end)
    return qs.aggregate(total=Sum("cost_micros"))["total"] or 0


def sales_overview_stats(organization_id: int, period: str) -> dict:
    now = timezone.now()
    start, prev_start = _window(period, now)

    open_qs = Conversation.objects.filter(organization_id=organization_id, lifecycle=LifecycleState.OPEN)
    open_dialogs = open_qs.count()
    waiting = open_qs.filter(expected_responder=ExpectedResponder.OPERATOR).count()
    ops = {
        "openDialogs": open_dialogs,
        "activeNow": open_qs.filter(last_activity_at__gte=now - _ACTIVE_WINDOW).count(),
        "onAI": open_qs.filter(control_mode=ControlMode.AI).count(),
        "onOperators": open_qs.filter(control_mode=ControlMode.HUMAN).count(),
        "waiting": waiting,
    }

    period_qs = Conversation.objects.filter(organization_id=organization_id, created_at__gte=start)
    period_block = {
        "dialogs": period_qs.count(),
        "dialogsPrev": Conversation.objects.filter(
            organization_id=organization_id, created_at__gte=prev_start, created_at__lt=start
        ).count(),
        "messages": Message.objects.filter(conversation__organization_id=organization_id, created_at__gte=start).count(),
        "aiCostMicros": _ai_cost(organization_id, start),
        "aiCostPrevMicros": _ai_cost(organization_id, prev_start, start),
    }

    open_by_channel = dict(open_qs.values_list("channel_id").annotate(c=Count("id")))
    period_by_channel = dict(period_qs.values_list("channel_id").annotate(c=Count("id")))

    by_channel: list[dict] = []
    by_product: dict[str, dict] = {}
    for channel in channels_for_organization(organization_id):
        open_count = open_by_channel.get(channel.id, 0)
        period_count = period_by_channel.get(channel.id, 0)
        by_channel.append({"code": channel.code, "name": channel.name, "openDialogs": open_count, "dialogs": period_count})
        if channel.product_id:
            bucket = by_product.setdefault(
                channel.product.code,
                {"code": channel.product.code, "name": channel.product.name, "openDialogs": 0, "dialogs": 0},
            )
            bucket["openDialogs"] += open_count
            bucket["dialogs"] += period_count

    problems = []
    for conversation in (
        open_qs.filter(expected_responder=ExpectedResponder.OPERATOR)
        .select_related("contact", "channel", "channel__product")
        .order_by("last_activity_at")[:5]
    ):
        minutes = int((now - conversation.last_activity_at).total_seconds() // 60)
        meta = conversation.channel.name
        problems.append(
            {
                "title": conversation.contact.name or "Гость",
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
        "chart": _chart(organization_id, period, start, now),
        "problems": problems,
    }
