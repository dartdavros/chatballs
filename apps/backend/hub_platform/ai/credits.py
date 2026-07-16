from __future__ import annotations

import logging

from django.db import transaction

from hub_platform.ai.models import LlmInvocation
from hub_platform.subscriptions.errors import EntitlementRequired
from hub_platform.subscriptions.keys import EntitlementKey, QuotaKey
from hub_platform.subscriptions.policy import get_effective_policy
from hub_platform.subscriptions.usage_service import record_usage
from hub_platform.tenancy.context import TenantContext

logger = logging.getLogger(__name__)

# Managed AI credit accounting. A successful LLM invocation consumes credits from
# the organization's monthly pool. The conversion from provider cost (micros) to
# credits is intentionally 1:1 here; the commercial rounding rules per PlanVersion
# (track B) will refine this once the managed provider catalog lands.
CREDITS_PER_COST_MICRO = 1


def assert_managed_ai_entitlement(*, channel) -> None:
    """C07 entitlement gate for platform-managed LLM usage. Raises
    EntitlementRequired if the organization's plan does not grant managed_ai."""
    context = TenantContext.for_resource(channel.organization)
    try:
        policy = get_effective_policy(context)
    except Exception as error:
        # No subscription: the AI runtime treats this as a hard stop so a tenant
        # without provisioning cannot incur managed cost.
        raise EntitlementRequired(EntitlementKey.MANAGED_AI) from error
    if not policy.has_entitlement(EntitlementKey.MANAGED_AI):
        raise EntitlementRequired(EntitlementKey.MANAGED_AI)


def consume_invocation_credits(*, channel, invocation: LlmInvocation) -> None:
    """Record managed-AI-credit usage for a successful invocation.

    Best-effort: a PolicyUnavailable / QuotaExceeded is logged but does not fail
    the already-completed LLM call (the cost was incurred). Quota enforcement for
    managed AI belongs at the preflight (limits) layer; here we only account.
    """
    cost = invocation.cost_micros or 0
    if cost <= 0:
        return
    credits = cost * CREDITS_PER_COST_MICRO
    context = TenantContext.for_resource(channel.organization)
    try:
        with transaction.atomic():
            record_usage(
                context=context,
                quota_key=QuotaKey.MANAGED_AI_CREDITS,
                quantity=credits,
                idempotency_key=f"invocation:{invocation.id}",
                source="ai.managed_invocation",
                aggregate_type="LlmInvocation",
                aggregate_id=str(invocation.id),
            )
    except Exception:  # pragma: no cover - accounting must not break the chat
        logger.exception("Failed to account managed AI credits for invocation %s", invocation.id)
