from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from hub_platform.identity.audit import record_audit_event
from hub_platform.subscriptions.subscription_models import Subscription, SubscriptionStatus
from hub_platform.subscriptions.subscription_service import _next_month
from hub_platform.subscriptions.usage_models import UsagePeriod, UsagePeriodStatus
from hub_platform.tenancy.context import TenantContext


@transaction.atomic
def activate_owner_subscription(*, context: TenantContext) -> Subscription:
    """Reactivate a subscription suspended as OWNER_PENDING and open the first
    usage period (SPEC-HUB-0021 §8.1). Idempotent: a subscription already ACTIVE
    with an open period is returned unchanged."""
    subscription = (
        Subscription.objects.select_for_update().get(organization_id=context.organization_id)
    )
    if subscription.status == SubscriptionStatus.ACTIVE:
        return subscription
    now = timezone.now()
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.suspension_reason = ""
    subscription.current_period_start = now
    subscription.current_period_end = _next_month(now)
    subscription.save(
        update_fields=[
            "status",
            "suspension_reason",
            "current_period_start",
            "current_period_end",
            "updated_at",
        ]
    )
    if not UsagePeriod.objects.filter(
        subscription=subscription, status=UsagePeriodStatus.OPEN
    ).exists():
        UsagePeriod.objects.create(
            organization=subscription.organization,
            subscription=subscription,
            starts_at=subscription.current_period_start,
            ends_at=subscription.current_period_end,
        )
    record_audit_event(
        action="subscription.activated",
        actor=context.actor_user,
        organization=context.organization,
        object_type="Subscription",
        object_id=str(subscription.id),
        payload={"status": subscription.status},
    )
    return subscription
