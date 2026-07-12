"""Командный центр: реальная сводка уровня компании (без выдуманных чисел).

Оба отдела (sales/support) с живыми метриками диалогов; коммерция — в карточке
продаж (заказы не привязаны к отделу). «Требует внимания» и состояние
интеграций — из реальных данных; расходы AI — из LlmInvocation.
"""

from __future__ import annotations

from django.conf import settings
from django.db.models import Count, Sum
from django.utils import timezone

from hub_platform.ai.models import AIAgent, LlmInvocation
from hub_platform.conversations.models import Conversation, ControlMode, LifecycleState
from hub_platform.conversations.stats import _ACTIVE_WINDOW, _window
from hub_platform.identity.models import Department, DepartmentStatus, EmployeeProfile
from hub_platform.integrations.models import Integration, IntegrationKind, IntegrationStatus
from hub_platform.orders.models import FulfillmentStatus, Order, PaymentStatus

_DEPT_ROUTE = {"sales": "salesOverview", "support": "supportOverview"}


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


def command_center_overview(organization_id: int, period: str) -> dict:
    now = timezone.now()
    start, _ = _window(period, now)

    open_qs = Conversation.objects.filter(organization_id=organization_id, lifecycle=LifecycleState.OPEN)
    paid = Order.objects.filter(organization_id=organization_id, payment_status=PaymentStatus.PAID, paid_at__gte=start)
    pending_orders = Order.objects.filter(organization_id=organization_id, payment_status=PaymentStatus.PENDING)
    fulfillment_errors = Order.objects.filter(organization_id=organization_id, fulfillment_status=FulfillmentStatus.FAILED)
    revenue = paid.aggregate(total=Sum("amount_minor"))["total"] or 0

    employees_by_dept = dict(
        EmployeeProfile.objects.filter(
            organization_id=organization_id, blocked_at__isnull=True, primary_department__isnull=False
        )
        .values_list("primary_department_id")
        .annotate(c=Count("id"))
    )
    agents_by_dept = dict(
        AIAgent.objects.filter(channel__organization_id=organization_id, is_active=True, channel__department__isnull=False)
        .values_list("channel__department_id")
        .annotate(c=Count("id"))
    )

    departments = []
    for department in Department.objects.filter(organization_id=organization_id, status=DepartmentStatus.ACTIVE).order_by("created_at"):
        dept_open = open_qs.filter(channel__department=department)
        block = {
            "code": department.code,
            "name": department.name,
            "route": _DEPT_ROUTE.get(department.code, "command"),
            "employees": employees_by_dept.get(department.id, 0),
            "aiAgents": agents_by_dept.get(department.id, 0),
            "dialogs": _dialog_block(dept_open, now),
        }
        if department.code == "sales":
            block["commerce"] = {
                "pendingPayments": pending_orders.count(),
                "fulfillmentErrors": fulfillment_errors.count(),
                "sales": paid.count(),
                "revenueMinor": revenue,
            }
        departments.append(block)

    # «Требует внимания»: очередь диалогов + незавершённые платежи + ошибки интеграций.
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
    for order in pending_orders.select_related("product").order_by("-created_at")[:3]:
        attention.append(
            {
                "kind": "payment",
                "title": f"Незавершённый платёж · {order.code}",
                "meta": f"Продажи · {order.product.name}" if order.product_id else "Продажи",
                "minutes": _minutes_since(order.created_at, now),
            }
        )

    integrations = []
    error_count = 0
    for integration in Integration.objects.filter(organization_id=organization_id):
        if integration.kind == IntegrationKind.LLM_PROVIDER:
            group = "AI-провайдер"
        elif integration.config.get("purpose") == "notifications":
            group = "Бот уведомлений"
        else:
            group = "Канал"
        if integration.status == IntegrationStatus.ERROR:
            error_count += 1
            attention.append(
                {
                    "kind": "integration",
                    "title": f"Ошибка интеграции · {integration.name}",
                    "meta": group,
                    "minutes": _minutes_since(integration.last_checked_at or integration.updated_at, now),
                }
            )
        integrations.append({"name": integration.name, "group": group, "status": integration.status})

    invocations = LlmInvocation.objects.filter(channel__organization_id=organization_id, created_at__gte=start)
    ai_totals = invocations.aggregate(cost=Sum("cost_micros"), tokens=Sum("total_tokens"))
    period_dialogs = Conversation.objects.filter(organization_id=organization_id, created_at__gte=start).count()

    total_waiting = sum(d["dialogs"]["waiting"] for d in departments)
    if error_count or fulfillment_errors.exists():
        status = "critical"
    elif total_waiting or pending_orders.exists():
        status = "attention"
    else:
        status = "ok"

    return {
        "period": period,
        "generatedAt": now.isoformat(),
        "company": {
            "status": status,
            "departments": len(departments),
            "openDialogs": open_qs.count(),
            "revenueMinor": revenue,
        },
        "departments": departments,
        "attention": attention,
        "integrations": integrations,
        "ai": {
            "spendMicros": ai_totals["cost"] or 0,
            # Дневной лимит стоимости (USD micros); 0 = не задан. Прогресс-бар
            # осмыслен только для периода «Сегодня».
            "dailyLimitMicros": int(getattr(settings, "HUB_AI_GLOBAL_DAILY_COST_LIMIT_MICROS", 0) or 0),
            "tokens": ai_totals["tokens"] or 0,
            "dialogs": period_dialogs,
        },
    }
