from __future__ import annotations

from hub_platform.subscriptions.keys import PlanCode, QuotaKey
from hub_platform.subscriptions.models import (
    EntitlementDefinition,
    EntitlementGrant,
    Plan,
    PlanVersion,
    QuotaDefinition,
    QuotaGrant,
    QuotaLimitSource,
    QuotaMode,
    Subscription,
)
from hub_platform.subscriptions.plan_service import publish_plan_version
from hub_platform.subscriptions.subscription_service import create_subscription
from hub_platform.tenancy.context import TenantActorKind, TenantContext


def ensure_default_subscription(organization, *, quantity: int = 3) -> Subscription:
    """Ensure an existing organization has an active subscription on the STARTUP
    plan. Used by bootstrap/seed so an organization is usable after C07 (every
    tenant operation requires an active subscription). Idempotent: returns the
    existing subscription if one already exists.

    The plan/version/grants are created on demand (rather than relying on the
    0002_seed_plan_drafts data migration) so this works under TransactionTestCase,
    which flushes migrated seed data between tests.
    """
    existing = Subscription.objects.filter(organization=organization).first()
    if existing is not None:
        return existing
    version = _startup_plan_version()
    context = TenantContext.for_resource(organization, actor_kind=TenantActorKind.SYSTEM)
    return create_subscription(
        context=context,
        plan_version=version,
        ai_agent_quantity=quantity,
    )


def _startup_plan_version() -> PlanVersion:
    plan, _ = Plan.objects.get_or_create(
        code=PlanCode.STARTUP,
        defaults={"name": "Стартап", "saleable": True},
    )
    version, created = PlanVersion.objects.get_or_create(
        plan=plan,
        version=1,
        defaults={"agent_unit_price_minor": 290_000, "currency": "RUB", "billing_period": "MONTH"},
    )
    if created:
        entitlement, _ = EntitlementDefinition.objects.get_or_create(
            key="byok_ai", defaults={"name": "BYOK AI"}
        )
        EntitlementGrant.objects.get_or_create(plan_version=version, definition=entitlement)
        slots_quota, _ = QuotaDefinition.objects.get_or_create(
            key=QuotaKey.AI_AGENT_SLOTS, defaults={"name": "AI agent slots", "unit": "slots"}
        )
        QuotaGrant.objects.get_or_create(
            plan_version=version,
            definition=slots_quota,
            defaults={
                "mode": QuotaMode.HARD,
                "limit_source": QuotaLimitSource.SUBSCRIPTION_AI_AGENT_QUANTITY,
            },
        )
        # C07: concurrent_p2p_calls derives from the active non-OWNER membership
        # count, matching the published STARTUP PlanVersion (PLAN §12).
        _ensure_membership_quota(
            version,
            QuotaKey.CONCURRENT_P2P_CALLS,
            "calls",
        )
    if version.published_at is None:
        version = publish_plan_version(version)
    return version


def _ensure_membership_quota(version, key, unit) -> None:
    """Grant a CONCURRENT quota whose limit is derived at read time from the active
    non-OWNER membership count (C07 MEMBERSHIP_COUNT)."""
    quota, _ = QuotaDefinition.objects.get_or_create(
        key=key, defaults={"name": key.replace("_", " "), "unit": unit}
    )
    QuotaGrant.objects.get_or_create(
        plan_version=version,
        definition=quota,
        defaults={
            "mode": QuotaMode.CONCURRENT,
            "limit_source": QuotaLimitSource.MEMBERSHIP_COUNT,
            "limit_value": None,
        },
    )
