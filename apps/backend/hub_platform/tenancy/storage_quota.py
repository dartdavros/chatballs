from __future__ import annotations

from django.db import transaction
from django.db.models import F

from hub_platform.subscriptions.errors import QuotaExceeded
from hub_platform.subscriptions.policy import get_effective_policy
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.models import OrganizationStorageUsage, StorageReservation
from hub_platform.tenancy.storage import STORAGE_QUOTA_KEY


@transaction.atomic
def reserve_storage(
    *, context: TenantContext, expected_bytes: int, idempotency_key: str
) -> StorageReservation:
    """SPEC §10 step 1: reserve the expected upload size against ``storage_bytes``
    before the object is persisted. Idempotent on (organization, idempotency_key):
    a replay returns the existing reservation without reserving a second time.

    Raises ``QuotaExceeded`` (mode=HARD) when ``bytes_used + reserved + expected``
    would exceed the quota. A missing policy/UNLIMITED quota is a no-op so a tenant
    without an active subscription is not silently blocked at upload.
    """
    usage = _locked_usage(context)
    existing = _active_reservation(context, idempotency_key)
    if existing is not None:
        return existing

    _assert_capacity(context, usage, expected_bytes)
    usage.reserved_bytes = F("reserved_bytes") + expected_bytes
    usage.save(update_fields=["reserved_bytes", "updated_at"])
    return StorageReservation.objects.create(
        organization=context.organization,
        idempotency_key=idempotency_key,
        reserved_bytes=expected_bytes,
    )


@transaction.atomic
def finalize_storage(
    *, context: TenantContext, idempotency_key: str, actual_bytes: int
) -> None:
    """SPEC §10 steps 2-3: settle a reservation once the actual object size is known.

    Moves ``reserved_bytes`` into ``bytes_used`` (commit), correcting for the delta
    between the reserved estimate and the real size: a shortfall releases the
    difference, an overrun consumes it (and is itself quota-checked). Idempotent: a
    finalized/released reservation is a no-op so retries are safe.
    """
    usage = _locked_usage(context)
    reservation = _active_reservation(context, idempotency_key)
    if reservation is None:
        return
    delta = actual_bytes - reservation.reserved_bytes
    if delta > 0:
        # Overrun: the reservation underestimated; consume the extra against the cap.
        _assert_capacity(context, usage, delta)
    # Release the reservation slot then commit the actual size as used storage.
    usage.reserved_bytes = F("reserved_bytes") - reservation.reserved_bytes
    usage.bytes_used = F("bytes_used") + actual_bytes
    usage.save(update_fields=["reserved_bytes", "bytes_used", "updated_at"])
    reservation.finalized = True
    reservation.save(update_fields=["finalized", "updated_at"])


@transaction.atomic
def release_storage(*, context: TenantContext, idempotency_key: str) -> None:
    """SPEC §10 step 4: release a reservation on upload failure. Idempotent: a
    missing or already settled reservation is a no-op, so failure paths are safe to
    retry."""
    usage = _locked_usage(context)
    reservation = _active_reservation(context, idempotency_key)
    if reservation is None:
        return
    usage.reserved_bytes = F("reserved_bytes") - reservation.reserved_bytes
    usage.save(update_fields=["reserved_bytes", "updated_at"])
    reservation.released = True
    reservation.save(update_fields=["released", "updated_at"])


def _locked_usage(context: TenantContext) -> OrganizationStorageUsage:
    usage, _ = OrganizationStorageUsage.objects.select_for_update().get_or_create(
        organization=context.organization,
        defaults={"bytes_used": 0, "reserved_bytes": 0},
    )
    return usage


def _active_reservation(
    context: TenantContext, idempotency_key: str
) -> StorageReservation | None:
    return (
        StorageReservation.objects.select_for_update()
        .filter(
            organization_id=context.organization_id,
            idempotency_key=idempotency_key,
            finalized=False,
            released=False,
        )
        .first()
    )


def _assert_capacity(
    context: TenantContext,
    usage: OrganizationStorageUsage,
    requested_bytes: int,
) -> None:
    try:
        policy = get_effective_policy(context)
    except Exception:
        return
    quota = policy.quota(STORAGE_QUOTA_KEY)
    if quota is None or quota.limit is None:
        return
    effective_used = usage.bytes_used + usage.reserved_bytes
    if effective_used + requested_bytes > quota.limit:
        raise QuotaExceeded(
            resource=STORAGE_QUOTA_KEY,
            limit=quota.limit,
            used=effective_used,
            requested=requested_bytes,
            mode=quota.mode,
        )
