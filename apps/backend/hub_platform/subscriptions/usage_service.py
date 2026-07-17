from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from hub_platform.identity.audit import record_audit_event
from hub_platform.subscriptions.errors import PolicyUnavailable, QuotaExceeded, UsageConflict
from hub_platform.subscriptions.models import (
    QuotaDefinition,
    QuotaMode,
    Subscription,
    UsageCounter,
    UsageEntryKind,
    UsageLedgerEntry,
    UsagePeriod,
    UsagePeriodStatus,
)
from hub_platform.subscriptions.policy import get_effective_policy
from hub_platform.tenancy.context import TenantContext


@dataclass(frozen=True, slots=True)
class UsageResult:
    entry: UsageLedgerEntry
    used_value: int


def _locked_period(context: TenantContext) -> UsagePeriod:
    try:
        subscription = Subscription.objects.get(organization_id=context.organization_id)
        return UsagePeriod.objects.select_for_update().get(
            organization_id=context.organization_id,
            subscription=subscription,
            status=UsagePeriodStatus.OPEN,
        )
    except (Subscription.DoesNotExist, UsagePeriod.DoesNotExist) as error:
        raise PolicyUnavailable("Organization has no open usage period") from error


def _same_usage(
    entry: UsageLedgerEntry,
    definition: QuotaDefinition,
    quantity: int,
    source: str,
    aggregate_type: str,
    aggregate_id: str,
) -> bool:
    return (
        entry.quota_definition_id == definition.id
        and entry.quantity == quantity
        and entry.source == source
        and entry.aggregate_type == aggregate_type
        and entry.aggregate_id == aggregate_id
    )


@transaction.atomic
def record_usage(
    *,
    context: TenantContext,
    quota_key: str,
    quantity: int,
    idempotency_key: str,
    source: str,
    aggregate_type: str = "",
    aggregate_id: str = "",
    metadata: dict | None = None,
    occurred_at=None,
    kind: str | None = None,
    correction_of: UsageLedgerEntry | None = None,
    rule_version: str | None = None,
) -> UsageResult:
    if quantity == 0:
        raise UsageConflict("Usage quantity cannot be zero")
    policy = get_effective_policy(context, require_active=quantity > 0)
    quota = policy.quota(quota_key)
    if quota is None:
        raise PolicyUnavailable(f"No quota policy for {quota_key}")
    definition = QuotaDefinition.objects.get(key=quota_key)
    period = _locked_period(context)
    existing = UsageLedgerEntry.objects.filter(
        organization_id=context.organization_id,
        idempotency_key=idempotency_key,
    ).first()
    if existing is not None:
        if not _same_usage(
            existing,
            definition,
            quantity,
            source,
            aggregate_type,
            aggregate_id,
        ):
            raise UsageConflict("Idempotency key was used for different usage")
        counter = UsageCounter.objects.get(period=period, quota_definition=definition)
        return UsageResult(entry=existing, used_value=counter.used_value)

    counter, _ = UsageCounter.objects.select_for_update().get_or_create(
        organization=context.organization,
        period=period,
        quota_definition=definition,
    )
    next_value = counter.used_value + quantity
    if next_value < 0:
        raise UsageConflict("Usage cannot become negative")
    if (
        quantity > 0
        and quota.mode in {QuotaMode.HARD, QuotaMode.RATE, QuotaMode.CONCURRENT}
        and quota.limit is not None
        and next_value + counter.reserved_value > quota.limit * definition.accounting_scale
    ):
        raise QuotaExceeded(
            resource=quota_key,
            limit=quota.limit * definition.accounting_scale,
            used=counter.used_value + counter.reserved_value,
            requested=quantity,
            period_ends_at=period.ends_at,
            mode=quota.mode,
        )
    entry_kind = kind or (
        UsageEntryKind.CONSUMPTION if quantity > 0 else UsageEntryKind.RELEASE
    )
    entry = UsageLedgerEntry.objects.create(
        organization=context.organization,
        period=period,
        quota_definition=definition,
        kind=entry_kind,
        quantity=quantity,
        unit=definition.accounting_unit or definition.unit,
        source=source,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        idempotency_key=idempotency_key,
        rule_version=rule_version or f"subscription:{policy.subscription_id}",
        metadata=metadata or {},
        correction_of=correction_of,
        occurred_at=occurred_at or timezone.now(),
    )
    counter.used_value = next_value
    counter.save(update_fields=["used_value", "updated_at"])
    return UsageResult(entry=entry, used_value=next_value)


@transaction.atomic
def record_adjustment(
    *,
    context: TenantContext,
    quota_key: str,
    quantity: int,
    idempotency_key: str,
    reason: str,
    correction_of: UsageLedgerEntry | None = None,
) -> UsageResult:
    if not reason.strip():
        raise UsageConflict("Usage adjustment requires a reason")
    result = record_usage(
        context=context,
        quota_key=quota_key,
        quantity=quantity,
        idempotency_key=idempotency_key,
        source="platform.adjustment",
        metadata={"reason": reason},
        kind=UsageEntryKind.ADJUSTMENT,
        correction_of=correction_of,
    )
    record_audit_event(
        action="subscription.usage_adjusted",
        actor=context.actor_user,
        organization=context.organization,
        object_type="UsageLedgerEntry",
        object_id=str(result.entry.id),
        payload={"quota": quota_key, "quantity": quantity, "reason": reason},
    )
    return result


@transaction.atomic
def rebuild_counter(
    *,
    context: TenantContext,
    quota_key: str,
) -> UsageCounter:
    definition = QuotaDefinition.objects.get(key=quota_key)
    period = _locked_period(context)
    total = (
        UsageLedgerEntry.objects.filter(period=period, quota_definition=definition).aggregate(
            total=Sum("quantity")
        )["total"]
        or 0
    )
    if total < 0:
        raise UsageConflict("Ledger rebuild produced negative usage")
    counter, _ = UsageCounter.objects.select_for_update().get_or_create(
        organization=context.organization,
        period=period,
        quota_definition=definition,
    )
    counter.used_value = total
    counter.save(update_fields=["used_value", "updated_at"])
    return counter
