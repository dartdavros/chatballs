from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Q
from django.utils import timezone

from hub_platform.subscriptions.errors import (
    EntitlementRequired,
    PolicyUnavailable,
    SubscriptionInactive,
)
from hub_platform.subscriptions.models import (
    OverrideOperation,
    QuotaLimitSource,
    QuotaMode,
    Subscription,
    SubscriptionOverride,
    SubscriptionStatus,
)
from hub_platform.tenancy.context import TenantContext


@dataclass(frozen=True, slots=True)
class EffectiveQuota:
    key: str
    mode: str
    limit: int | None
    unit: str
    window_seconds: int | None


@dataclass(frozen=True, slots=True)
class EffectivePolicy:
    subscription_id: int
    status: str
    entitlements: frozenset[str]
    quotas: dict[str, EffectiveQuota]

    def has_entitlement(self, key: str) -> bool:
        return key in self.entitlements

    def quota(self, key: str) -> EffectiveQuota | None:
        return self.quotas.get(key)


def _subscription(context: TenantContext) -> Subscription:
    try:
        return (
            Subscription.objects.select_related("plan_version", "organization")
            .prefetch_related(
                "plan_version__entitlement_grants__definition",
                "plan_version__quota_grants__definition",
            )
            .get(organization_id=context.organization_id)
        )
    except Subscription.DoesNotExist as error:
        raise PolicyUnavailable("Organization has no subscription") from error


def _active_overrides(context: TenantContext, at) -> list[SubscriptionOverride]:
    return list(
        SubscriptionOverride.objects.select_related(
            "entitlement_definition", "quota_definition"
        )
        .filter(organization_id=context.organization_id, starts_at__lte=at)
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=at))
        .order_by("created_at", "id")
    )


def get_effective_policy(
    context: TenantContext,
    *,
    at=None,
    require_active: bool = False,
) -> EffectivePolicy:
    subscription = _subscription(context)
    active = subscription.status in {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.GRACE_PERIOD,
    }
    if require_active and not active:
        raise SubscriptionInactive(f"Subscription is {subscription.status}")

    entitlements = {
        grant.definition.key
        for grant in subscription.plan_version.entitlement_grants.all()
        if grant.enabled
    }
    quotas: dict[str, EffectiveQuota] = {}
    for grant in subscription.plan_version.quota_grants.all():
        limit = grant.limit_value
        if grant.limit_source == QuotaLimitSource.SUBSCRIPTION_AI_AGENT_QUANTITY:
            limit = subscription.ai_agent_quantity
        quotas[grant.definition.key] = EffectiveQuota(
            key=grant.definition.key,
            mode=grant.mode,
            limit=None if grant.mode == QuotaMode.UNLIMITED else limit,
            unit=grant.definition.unit,
            window_seconds=grant.window_seconds,
        )

    for override in _active_overrides(context, at or timezone.now()):
        if override.entitlement_definition_id:
            key = override.entitlement_definition.key
            if override.operation == OverrideOperation.ENABLE:
                entitlements.add(key)
            else:
                entitlements.discard(key)
            continue
        key = override.quota_definition.key
        current = quotas.get(key)
        if current is None:
            current = EffectiveQuota(
                key=key,
                mode=QuotaMode.HARD,
                limit=0,
                unit=override.quota_definition.unit,
                window_seconds=None,
            )
        base = current.limit or 0
        limit = override.value if override.operation == OverrideOperation.SET else base + override.value
        mode = (
            QuotaMode.HARD
            if override.operation == OverrideOperation.SET and current.mode == QuotaMode.UNLIMITED
            else current.mode
        )
        quotas[key] = EffectiveQuota(
            key=key,
            mode=mode,
            limit=max(0, limit),
            unit=current.unit,
            window_seconds=current.window_seconds,
        )

    if not active:
        entitlements.clear()
        quotas = {
            key: EffectiveQuota(
                key=value.key,
                mode=value.mode,
                limit=0,
                unit=value.unit,
                window_seconds=value.window_seconds,
            )
            for key, value in quotas.items()
        }
    return EffectivePolicy(
        subscription_id=subscription.id,
        status=subscription.status,
        entitlements=frozenset(entitlements),
        quotas=quotas,
    )


def require_entitlement(context: TenantContext, key: str) -> None:
    policy = get_effective_policy(context, require_active=True)
    if not policy.has_entitlement(key):
        raise EntitlementRequired(key)
