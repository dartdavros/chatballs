from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from hub_platform.subscriptions.errors import (
    PolicyUnavailable,
    QuotaExceeded,
)
from hub_platform.subscriptions.models import (
    QuotaDefinition,
    QuotaMode,
    UsageCounter,
    UsagePeriod,
    UsagePeriodStatus,
    UsageReservation,
)
from hub_platform.subscriptions.policy import get_effective_policy
from hub_platform.tenancy.context import TenantContext


@dataclass(frozen=True, slots=True)
class ReservationResult:
    reservation: UsageReservation
    reserved_value: int


def _locked_period(context: TenantContext) -> UsagePeriod:
    try:
        return UsagePeriod.objects.select_for_update().get(
            organization_id=context.organization_id,
            status=UsagePeriodStatus.OPEN,
        )
    except UsagePeriod.DoesNotExist as error:
        raise PolicyUnavailable("Organization has no open usage period") from error


def _quota_definition(quota_key: str) -> QuotaDefinition:
    try:
        return QuotaDefinition.objects.get(key=quota_key)
    except QuotaDefinition.DoesNotExist as error:
        raise PolicyUnavailable(f"Unknown quota: {quota_key}") from error


@transaction.atomic
def reserve_usage(
    *,
    context: TenantContext,
    quota_key: str,
    idempotency_key: str,
    lease_seconds: int,
    source: str,
    aggregate_type: str = "",
    aggregate_id: str = "",
) -> ReservationResult:
    """Acquire a slot on a CONCURRENT-mode quota for a live session (SPEC §7).

    Idempotent on (organization, idempotency_key): a replay returns the existing
    reservation without taking a second slot. Raises QuotaExceeded (mode=CONCURRENT)
    if the active-reservation count exceeds the limit.
    """
    period = _locked_period(context)
    definition = _quota_definition(quota_key)

    existing = UsageReservation.objects.filter(
        organization_id=context.organization_id,
        idempotency_key=idempotency_key,
    ).first()
    if existing is not None:
        # Replay: refresh the lease and return without a second slot.
        existing.expires_at = timezone.now() + timedelta(seconds=lease_seconds)
        existing.save(update_fields=["expires_at"])
        return ReservationResult(
            reservation=existing,
            reserved_value=_reserved_value(context, definition, period),
        )

    policy = get_effective_policy(context)
    quota = policy.quota(quota_key)
    if quota is None:
        raise PolicyUnavailable(f"Quota not granted: {quota_key}")
    if quota.limit is not None and quota.mode in {
        QuotaMode.HARD,
        QuotaMode.RATE,
        QuotaMode.CONCURRENT,
    }:
        counter, _ = UsageCounter.objects.select_for_update().get_or_create(
            organization_id=context.organization_id,
            period=period,
            quota_definition=definition,
        )
        current = counter.used_value + counter.reserved_value
        if current + 1 > quota.limit:
            raise QuotaExceeded(
                resource=quota_key,
                limit=quota.limit,
                used=current,
                requested=1,
                period_ends_at=period.ends_at,
                mode=quota.mode,
            )
        counter.reserved_value = F("reserved_value") + 1
        counter.save(update_fields=["reserved_value"])

    reservation = UsageReservation.objects.create(
        organization_id=context.organization_id,
        period=period,
        quota_definition=definition,
        idempotency_key=idempotency_key,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        source=source,
        expires_at=timezone.now() + timedelta(seconds=lease_seconds),
    )
    return ReservationResult(
        reservation=reservation,
        reserved_value=_reserved_value(context, definition, period),
    )


@transaction.atomic
def release_usage(*, context: TenantContext, idempotency_key: str) -> None:
    """Release a previously acquired slot. Idempotent: a missing or already
    released reservation is a no-op (so terminal transitions are safe to retry)."""
    _locked_period(context)
    reservation = (
        UsageReservation.objects.select_for_update()
        .filter(
            organization_id=context.organization_id,
            idempotency_key=idempotency_key,
            released_at__isnull=True,
        )
        .first()
    )
    if reservation is None:
        return
    reservation.released_at = timezone.now()
    reservation.save(update_fields=["released_at"])
    UsageCounter.objects.filter(
        organization_id=context.organization_id,
        period=reservation.period_id,
        quota_definition=reservation.quota_definition,
    ).update(reserved_value=F("reserved_value") - 1)


@transaction.atomic
def expire_stale_reservations() -> int:
    """Cleanup worker entry: release reservations whose lease has lapsed without an
    explicit release (crashed/stuck sessions). Returns the count expired. Idempotent."""
    now = timezone.now()
    stale = list(
        UsageReservation.objects.select_for_update()
        .filter(released_at__isnull=True, expires_at__lte=now)
    )
    if not stale:
        return 0
    by_period_quota: dict[tuple[int, int], int] = {}
    for reservation in stale:
        reservation.released_at = now
        key = (reservation.period_id, reservation.quota_definition_id)
        by_period_quota[key] = by_period_quota.get(key, 0) + 1
    UsageReservation.objects.bulk_update(stale, ["released_at"])
    # Decrement reserved_value per counter in a single guarded update.
    for (period_id, definition_id), count in by_period_quota.items():
        counter = (
            UsageCounter.objects.select_for_update()
            .filter(period_id=period_id, quota_definition_id=definition_id)
            .first()
        )
        if counter is not None and counter.reserved_value > 0:
            counter.reserved_value = max(0, counter.reserved_value - count)
            counter.save(update_fields=["reserved_value"])
    return len(stale)


def _reserved_value(
    context: TenantContext, definition: QuotaDefinition, period: UsagePeriod
) -> int:
    counter = UsageCounter.objects.filter(
        organization_id=context.organization_id,
        period=period,
        quota_definition=definition,
    ).first()
    return counter.reserved_value if counter else 0
