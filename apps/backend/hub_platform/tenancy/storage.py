from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

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
