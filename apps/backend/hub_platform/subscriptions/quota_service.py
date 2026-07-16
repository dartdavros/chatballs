from __future__ import annotations

from hub_platform.subscriptions.models import UsageCounter, UsagePeriodStatus
from hub_platform.subscriptions.policy import get_effective_policy
from hub_platform.tenancy.context import TenantContext

# Advisory quota pre-check (SPEC-HUB-0022 §6). Non-authoritative: a concurrent
# request may still exceed the limit between check() and consume(). The
# authoritative gate is the atomic record_usage() / reserve_usage() write.


def check(
    context: TenantContext, quota_key: str, quantity: int = 1
) -> bool:
    """Return True if `quantity` more units would fit within the quota.

    Reads the current open-period counter (used + reserved) against the effective
    quota limit. UNLIMITED quotas always return True. Does not raise on a missing
    subscription/period (returns False) so callers can treat "no policy" as
    "deny" without exception handling.
    """
    try:
        policy = get_effective_policy(context)
    except Exception:
        return False
    quota = policy.quota(quota_key)
    if quota is None:
        return False
    if quota.limit is None:
        return True
    current = _current_usage(context, quota_key)
    return current + quantity <= quota.limit


def _current_usage(context: TenantContext, quota_key: str) -> int:
    counter = (
        UsageCounter.objects.select_related("quota_definition")
        .filter(
            organization_id=context.organization_id,
            quota_definition__key=quota_key,
            period__status=UsagePeriodStatus.OPEN,
        )
        .first()
    )
    if counter is None:
        return 0
    return counter.used_value + counter.reserved_value
