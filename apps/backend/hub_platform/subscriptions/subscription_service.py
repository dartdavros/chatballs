from __future__ import annotations

import calendar
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from hub_platform.identity.audit import record_audit_event
from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.models import (
    PlanVersion,
    QuotaDefinition,
    Subscription,
    SubscriptionStatus,
    UsageCounter,
    UsageEntryKind,
    UsageLedgerEntry,
    UsagePeriod,
)
from hub_platform.tenancy.context import TenantContext


def _next_month(value: datetime) -> datetime:
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _validate_quantity(plan_version: PlanVersion, quantity: int) -> None:
    if quantity < 1:
        raise ValidationError({"ai_agent_quantity": "Quantity must be positive"})
    fixed = plan_version.fixed_ai_agent_quantity
    if fixed is not None and quantity != fixed:
        raise ValidationError(
            {"ai_agent_quantity": f"This plan version requires quantity {fixed}"}
        )


def _open_period(subscription: Subscription, starts_at, ends_at) -> UsagePeriod:
    return UsagePeriod.objects.create(
        organization=subscription.organization,
        subscription=subscription,
        starts_at=starts_at,
        ends_at=ends_at,
    )


def _import_active_agent_slots(subscription: Subscription, period: UsagePeriod) -> None:
    from hub_platform.ai.models import AIAgent, AIAgentStatus

    agents = list(
        AIAgent.objects.filter(
            organization=subscription.organization,
            status=AIAgentStatus.ACTIVE,
        ).order_by("id")
    )
    if len(agents) > subscription.ai_agent_quantity:
        raise ValidationError(
            {"ai_agent_quantity": "Quantity is below the existing active AI-agent count"}
        )
    definition = QuotaDefinition.objects.get(key=QuotaKey.AI_AGENT_SLOTS)
    UsageCounter.objects.create(
        organization=subscription.organization,
        period=period,
        quota_definition=definition,
        used_value=len(agents),
    )
    now = timezone.now()
    for agent in agents:
        UsageLedgerEntry.objects.create(
            organization=subscription.organization,
            period=period,
            quota_definition=definition,
            kind=UsageEntryKind.OPENING_BALANCE,
            quantity=1,
            unit=definition.unit,
            source="subscription.initialization",
            aggregate_type="AIAgent",
            aggregate_id=str(agent.id),
            idempotency_key=f"ai-agent:{agent.id}:opening-balance",
            rule_version=f"plan-version:{subscription.plan_version.public_id}",
            occurred_at=now,
        )


@transaction.atomic
def create_subscription(
    *,
    context: TenantContext,
    plan_version: PlanVersion,
    ai_agent_quantity: int,
    status: str = SubscriptionStatus.ACTIVE,
    period_start=None,
    period_end=None,
    allow_unsaleable: bool = False,
) -> Subscription:
    plan_version = PlanVersion.objects.select_related("plan").get(pk=plan_version.pk)
    if plan_version.published_at is None:
        raise ValidationError({"plan_version": "Plan version is not published"})
    if not plan_version.quota_grants.filter(
        definition__key=QuotaKey.AI_AGENT_SLOTS
    ).exists():
        raise ValidationError({"plan_version": "Plan version has no AI-agent slot policy"})
    if not plan_version.plan.saleable and not allow_unsaleable:
        raise ValidationError({"plan_version": "Plan is not saleable"})
    _validate_quantity(plan_version, ai_agent_quantity)
    if Subscription.objects.filter(organization=context.organization).exists():
        raise ValidationError({"organization": "Organization already has a subscription"})

    if status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE_PERIOD}:
        period_start = period_start or timezone.now()
        period_end = period_end or _next_month(period_start)
    else:
        period_start = period_end = None
    subscription = Subscription(
        organization=context.organization,
        plan_version=plan_version,
        ai_agent_quantity=ai_agent_quantity,
        status=status,
        current_period_start=period_start,
        current_period_end=period_end,
    )
    subscription.full_clean()
    subscription.save()
    if period_start is not None:
        period = _open_period(subscription, period_start, period_end)
        _import_active_agent_slots(subscription, period)
    record_audit_event(
        action="subscription.created",
        actor=context.actor_user,
        organization=context.organization,
        object_type="Subscription",
        object_id=str(subscription.id),
        payload={
            "planVersionId": str(plan_version.public_id),
            "aiAgentQuantity": ai_agent_quantity,
            "status": status,
        },
    )
    return subscription


@transaction.atomic
def change_ai_agent_quantity(
    *,
    context: TenantContext,
    quantity: int,
) -> Subscription:
    subscription = (
        Subscription.objects.select_for_update()
        .select_related("plan_version")
        .get(organization_id=context.organization_id)
    )
    _validate_quantity(subscription.plan_version, quantity)
    from hub_platform.ai.models import AIAgent, AIAgentStatus

    active_count = AIAgent.objects.filter(
        organization_id=context.organization_id,
        status=AIAgentStatus.ACTIVE,
    ).count()
    if quantity < active_count:
        raise ValidationError(
            {"ai_agent_quantity": "Disable AI agents before reducing the quantity"}
        )
    previous = subscription.ai_agent_quantity
    if previous == quantity:
        return subscription
    subscription.ai_agent_quantity = quantity
    subscription.full_clean()
    subscription.save(update_fields=["ai_agent_quantity", "updated_at"])
    record_audit_event(
        action="subscription.ai_agent_quantity_changed",
        actor=context.actor_user,
        organization=context.organization,
        object_type="Subscription",
        object_id=str(subscription.id),
        payload={"previous": previous, "current": quantity},
    )
    return subscription
