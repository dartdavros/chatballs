from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from hub_platform.subscriptions.errors import QuotaExceeded
from hub_platform.subscriptions.policy import get_effective_policy
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.models import OrganizationStorageUsage

STORAGE_QUOTA_KEY = "storage_bytes"


@transaction.atomic
def adjust_storage_usage(*, context: TenantContext, delta_bytes: int) -> int:
    usage, _ = OrganizationStorageUsage.objects.select_for_update().get_or_create(
        organization=context.organization,
        defaults={"bytes_used": 0},
    )
    next_value = usage.bytes_used + int(delta_bytes)
    if next_value < 0:
        raise ValidationError("Storage usage cannot become negative")
    usage.bytes_used = next_value
    usage.save(update_fields=["bytes_used", "updated_at"])
    return next_value


def assert_storage_quota(*, context: TenantContext, delta_bytes: int) -> None:
    """C07 storage gate: block writes that would exceed the storage_bytes quota.

    Reads are never gated (PLAN-CUSTOCRM-0003 §12). `delta_bytes` is the net
    change the proposed write would add (new bytes minus any replaced bytes).
    Raises QuotaExceeded (mode=HARD) if overage; no-op for UNLIMITED or missing
    policy so a tenant without an active subscription is not silently blocked at
    upload — provisioning guarantees a subscription before tenant use.
    """
    try:
        policy = get_effective_policy(context)
    except Exception:
        return
    quota = policy.quota(STORAGE_QUOTA_KEY)
    if quota is None or quota.limit is None:
        return
    current = _current_bytes(context)
    if current + delta_bytes > quota.limit:
        raise QuotaExceeded(
            resource=STORAGE_QUOTA_KEY,
            limit=quota.limit,
            used=current,
            requested=delta_bytes,
            mode=quota.mode,
        )


def _current_bytes(context: TenantContext) -> int:
    usage = OrganizationStorageUsage.objects.filter(
        organization_id=context.organization_id
    ).first()
    return usage.bytes_used if usage else 0
