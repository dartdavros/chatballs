from hub_platform.subscriptions.keys import PlanCode
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
from hub_platform.testing import system_tenant_context


def create_test_subscription(organization, *, quantity: int = 1, plan_code=PlanCode.STARTUP):
    # Idempotent: if bootstrap or a prior call already created a subscription,
    # return it (C07 bootstrap now provisions a default subscription).
    existing = Subscription.objects.filter(organization=organization).first()
    if existing is not None:
        # Reconcile the ai_agent_slot counter with agents that may have been
        # activated directly (test fixtures bypass the gate) and align the
        # subscription quantity with what the test expects.
        _resync_agent_slots(organization, existing, quantity)
        return existing
    plan, _ = Plan.objects.get_or_create(
        code=plan_code,
        defaults={"name": "Test plan", "saleable": True},
    )
    version, created = PlanVersion.objects.get_or_create(
        plan=plan,
        version=1,
        defaults={
            "agent_unit_price_minor": 290_000,
            "currency": "RUB",
            "billing_period": "MONTH",
        },
    )
    if created:
        entitlement, _ = EntitlementDefinition.objects.get_or_create(
            key="byok_ai",
            defaults={"name": "BYOK AI"},
        )
        EntitlementGrant.objects.create(
            plan_version=version,
            definition=entitlement,
        )
        quota, _ = QuotaDefinition.objects.get_or_create(
            key="ai_agent_slots",
            defaults={"name": "AI agent slots", "unit": "slots"},
        )
        QuotaGrant.objects.create(
            plan_version=version,
            definition=quota,
            mode=QuotaMode.HARD,
            limit_source=QuotaLimitSource.SUBSCRIPTION_AI_AGENT_QUANTITY,
        )
    if version.published_at is None:
        version = publish_plan_version(version)
    return create_subscription(
        context=system_tenant_context(organization),
        plan_version=version,
        ai_agent_quantity=quantity,
    )


def _resync_agent_slots(organization, subscription, quantity: int) -> None:
    """Reconcile ai_agent_slots for an existing subscription so tests that create
    ACTIVE agents directly (bypassing the slot gate) keep the counter consistent,
    and align the subscription quantity with the requested value."""
    from hub_platform.ai.models import AIAgent, AIAgentStatus
    from hub_platform.subscriptions.models import QuotaDefinition, UsageCounter

    active = AIAgent.objects.filter(
        organization=organization, status=AIAgentStatus.ACTIVE
    ).count()
    target_quantity = max(quantity, active)
    if subscription.ai_agent_quantity != target_quantity:
        subscription.ai_agent_quantity = target_quantity
        subscription.save(update_fields=["ai_agent_quantity", "updated_at"])
    definition = QuotaDefinition.objects.filter(key="ai_agent_slots").first()
    if definition is not None:
        period = subscription.usage_periods.filter(status="OPEN").first()
        if period is not None:
            counter, _ = UsageCounter.objects.update_or_create(
                period=period,
                quota_definition=definition,
                defaults={"used_value": active},
            )
