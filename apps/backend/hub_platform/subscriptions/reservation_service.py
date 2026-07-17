from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from hub_platform.subscriptions.errors import (
    PolicyUnavailable,
    QuotaExceeded,
    UsageConflict,
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
    quantity: int = 1,
    reserve_up_to_available: bool = False,
) -> ReservationResult:
    """Reserve quota units for a live operation (SPEC §7).

    Idempotent on (organization, idempotency_key): a replay returns the existing
    reservation without taking units twice. Raises QuotaExceeded when the
    requested quantity does not fit the effective limit.
    """
    if quantity <= 0:
        raise UsageConflict("Reservation quantity must be positive")
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
        effective_limit = quota.limit * definition.accounting_scale
        available = effective_limit - current
        reserved_quantity = min(quantity, available) if reserve_up_to_available else quantity
        if reserved_quantity <= 0 or current + reserved_quantity > effective_limit:
            raise QuotaExceeded(
                resource=quota_key,
                limit=effective_limit,
                used=current,
                requested=max(1, reserved_quantity),
                period_ends_at=period.ends_at,
                mode=quota.mode,
            )
        counter.reserved_value = F("reserved_value") + reserved_quantity
        counter.save(update_fields=["reserved_value"])
    else:
        reserved_quantity = quantity

    reservation = UsageReservation.objects.create(
        organization_id=context.organization_id,
        period=period,
        quota_definition=definition,
        idempotency_key=idempotency_key,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        source=source,
        quantity=reserved_quantity,
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
    ).update(reserved_value=F("reserved_value") - reservation.quantity)


@transaction.atomic
def commit_usage_reservation(
    *,
    context: TenantContext,
    idempotency_key: str,
    quantity: int,
    metadata: dict | None = None,
    rule_version: str | None = None,
):
    """Atomically replace an active reservation with exact metered usage."""
    if quantity <= 0:
        raise UsageConflict("Committed usage quantity must be positive")
    _locked_period(context)
    reservation = UsageReservation.objects.select_for_update().get(
        organization_id=context.organization_id,
        idempotency_key=idempotency_key,
        released_at__isnull=True,
    )
    if quantity > reservation.quantity:
        raise UsageConflict("Committed usage exceeds reserved quantity")
    reservation.released_at = timezone.now()
    reservation.save(update_fields=["released_at"])
    UsageCounter.objects.filter(
        organization_id=context.organization_id,
        period=reservation.period_id,
        quota_definition=reservation.quota_definition,
    ).update(reserved_value=F("reserved_value") - reservation.quantity)

    from hub_platform.subscriptions.usage_service import record_usage

    return record_usage(
        context=context,
        quota_key=reservation.quota_definition.key,
        quantity=quantity,
        idempotency_key=idempotency_key,
        source=reservation.source,
        aggregate_type=reservation.aggregate_type,
        aggregate_id=reservation.aggregate_id,
        metadata=metadata,
        rule_version=rule_version,
    )


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
        by_period_quota[key] = by_period_quota.get(key, 0) + reservation.quantity
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
