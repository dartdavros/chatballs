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
)
from hub_platform.subscriptions.plan_service import publish_plan_version
from hub_platform.subscriptions.subscription_service import create_subscription
from hub_platform.testing import system_tenant_context


def create_test_subscription(organization, *, quantity: int = 1, plan_code=PlanCode.STARTUP):
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
