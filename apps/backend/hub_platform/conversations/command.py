"""Командный центр: реальная сводка уровня компании (без выдуманных чисел).

Отделы упразднены (ADR-HUB-0043): карточки строятся по настраиваемым группам
организации плюс блок «Без группы». «Требует внимания» и состояние интеграций —
из реальных данных; расходы AI — из LlmInvocation.
"""

from __future__ import annotations

from django.conf import settings
from django.db.models import Count, Sum
from django.utils import timezone

from hub_platform.ai.models import AIAgent, LlmInvocation
from hub_platform.conversations.models import Conversation, ControlMode, LifecycleState
from hub_platform.conversations.stats import _ACTIVE_WINDOW, _window
from hub_platform.identity.group_models import EmployeeGroup
from hub_platform.integrations.models import Integration, IntegrationKind, IntegrationStatus
from hub_platform.tenancy.context import TenantContext


def _dialog_block(open_qs, now) -> dict:
    return {
        "open": open_qs.count(),
        "activeNow": open_qs.filter(last_activity_at__gte=now - _ACTIVE_WINDOW).count(),
        "onAI": open_qs.filter(control_mode=ControlMode.AI).count(),
        "onOperators": open_qs.filter(control_mode=ControlMode.HUMAN).count(),
        # Очередь: никем не взятые (та же семантика, что бейдж «Диалоги»).
        "waiting": open_qs.filter(control_mode=ControlMode.PAUSED).count(),
    }


def _minutes_since(moment, now) -> int:
    return max(0, int((now - moment).total_seconds() // 60))


def command_center_overview(context: TenantContext, period: str) -> dict:
    organization_id = context.organization_id
    now = timezone.now()
    start, _ = _window(period, now)

    open_qs = Conversation.objects.filter(organization_id=organization_id, lifecycle=LifecycleState.OPEN)

    groups = list(
        EmployeeGroup.objects.filter(organization_id=organization_id)
        .annotate(member_count=Count("member_links", distinct=True))
        .order_by("name")
    )
    agents_by_group = dict(
        AIAgent.objects.filter(
            channel__organization_id=organization_id,
            status="ACTIVE",
            channel__group__isnull=False,
        )
        .values_list("channel__group_id")
        .annotate(c=Count("id"))
    )

    cards = []
    for group in groups:
        group_open = open_qs.filter(group=group)
        cards.append(
            {
                "code": str(group.id),
                "name": group.name,
                "route": "salesDialogs",
                "employees": group.member_count,
                "aiAgents": agents_by_group.get(group.id, 0),
                "dialogs": _dialog_block(group_open, now),
            }
        )
    ungrouped_open = open_qs.filter(group__isnull=True)
    if not groups or ungrouped_open.exists():
        cards.append(
            {
                "code": "none",
                "name": "Без группы",
                "route": "salesDialogs",
                "employees": 0,
                "aiAgents": AIAgent.objects.filter(
                    channel__organization_id=organization_id,
                    status="ACTIVE",
                    channel__group__isnull=True,
                ).count(),
                "dialogs": _dialog_block(ungrouped_open, now),
            }
        )

    # «Требует внимания»: очередь диалогов + ошибки интеграций.
    attention: list[dict] = []
    queue = (
        open_qs.filter(control_mode=ControlMode.PAUSED)
        .select_related("contact", "support_identity_snapshot", "channel")
        .order_by("last_activity_at")[:4]
    )
    for conversation in queue:
        snapshot = conversation.support_identity_snapshot
        who = (conversation.contact.name if conversation.contact_id else "") or (snapshot.display_name if snapshot else "") or "Гость"
        attention.append(
            {
                "kind": "dialog",
                "title": f"Диалог ждёт оператора · {who}",
                "meta": conversation.channel.name,
                "minutes": _minutes_since(conversation.last_activity_at, now),
            }
        )

    integrations = []
    error_count = 0
    for integration in Integration.objects.filter(organization_id=organization_id):
        if integration.kind == IntegrationKind.LLM_PROVIDER:
            group_label = "AI-провайдер"
        elif integration.config.get("purpose") == "notifications":
            group_label = "Бот уведомлений"
        else:
            group_label = "Канал"
        if integration.status == IntegrationStatus.ERROR:
            error_count += 1
            attention.append(
                {
                    "kind": "integration",
                    "title": f"Ошибка интеграции · {integration.name}",
                    "meta": group_label,
                    "minutes": _minutes_since(integration.last_checked_at or integration.updated_at, now),
                }
            )
        integrations.append({"name": integration.name, "group": group_label, "status": integration.status})

    invocations = LlmInvocation.objects.filter(channel__organization_id=organization_id, created_at__gte=start)
    ai_totals = invocations.aggregate(cost=Sum("cost_micros"), tokens=Sum("total_tokens"))
    period_dialogs = Conversation.objects.filter(organization_id=organization_id, created_at__gte=start).count()

    total_waiting = sum(card["dialogs"]["waiting"] for card in cards)
    if error_count:
        status = "critical"
    elif total_waiting:
        status = "attention"
    else:
        status = "ok"

    return {
        "period": period,
        "generatedAt": now.isoformat(),
        "company": {
            "status": status,
            "departments": len(cards),
            "openDialogs": open_qs.count(),
        },
        "departments": cards,
        "attention": attention,
        "integrations": integrations,
        "ai": {
            "spendMicros": ai_totals["cost"] or 0,
            # Дневной лимит стоимости (USD micros); 0 = не задан. Прогресс-бар
            # осмыслен только для периода «Сегодня».
            "dailyLimitMicros": int(getattr(settings, "CUS_AI_GLOBAL_DAILY_COST_LIMIT_MICROS", 0) or 0),
            "tokens": ai_totals["tokens"] or 0,
            "dialogs": period_dialogs,
        },
    }
