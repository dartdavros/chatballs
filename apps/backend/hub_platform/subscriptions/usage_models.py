from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from hub_platform.tenancy.models import TenantRelationModel


class UsagePeriodStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    CLOSED = "CLOSED", "Closed"


class UsageEntryKind(models.TextChoices):
    CONSUMPTION = "CONSUMPTION", "Consumption"
    RELEASE = "RELEASE", "Release"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"
    OPENING_BALANCE = "OPENING_BALANCE", "Opening balance"


class UsagePeriod(TenantRelationModel):
    tenant_relation_fields = ("subscription",)
    subscription = models.ForeignKey(
        "subscriptions.Subscription",
        on_delete=models.PROTECT,
        related_name="usage_periods",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(
        max_length=16,
        choices=UsagePeriodStatus.choices,
        default=UsagePeriodStatus.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-starts_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["subscription"],
                condition=Q(status=UsagePeriodStatus.OPEN),
                name="uniq_open_usage_period_per_subscription",
            ),
            models.CheckConstraint(
                condition=Q(ends_at__gt=models.F("starts_at")),
                name="subscription_usage_period_valid_bounds",
            ),
        ]


class UsageCounter(TenantRelationModel):
    tenant_relation_fields = ("period",)
    period = models.ForeignKey(
        UsagePeriod,
        on_delete=models.PROTECT,
        related_name="counters",
    )
    quota_definition = models.ForeignKey(
        "subscriptions.QuotaDefinition",
        on_delete=models.PROTECT,
        related_name="usage_counters",
    )
    used_value = models.PositiveBigIntegerField(default=0)
    reserved_value = models.PositiveBigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["period", "quota_definition"],
                name="uniq_usage_counter_period_quota",
            )
        ]


class UsageLedgerEntry(TenantRelationModel):
    tenant_relation_fields = ("period",)
    period = models.ForeignKey(
        UsagePeriod,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    quota_definition = models.ForeignKey(
        "subscriptions.QuotaDefinition",
        on_delete=models.PROTECT,
        related_name="usage_ledger_entries",
    )
    kind = models.CharField(max_length=32, choices=UsageEntryKind.choices)
    quantity = models.BigIntegerField()
    unit = models.CharField(max_length=32)
    source = models.CharField(max_length=64)
    aggregate_type = models.CharField(max_length=64, blank=True)
    aggregate_id = models.CharField(max_length=128, blank=True)
    idempotency_key = models.CharField(max_length=160)
    rule_version = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    correction_of = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="corrections",
        null=True,
        blank=True,
    )
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["organization", "quota_definition", "occurred_at"])
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"],
                name="uniq_usage_idempotency_per_organization",
            ),
            models.CheckConstraint(
                condition=~Q(quantity=0),
                name="subscription_usage_quantity_nonzero",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind=UsageEntryKind.CONSUMPTION, quantity__gt=0)
                    | Q(kind=UsageEntryKind.OPENING_BALANCE, quantity__gt=0)
                    | Q(kind=UsageEntryKind.RELEASE, quantity__lt=0)
                    | Q(kind=UsageEntryKind.ADJUSTMENT)
                ),
                name="subscription_usage_entry_sign",
            ),
            models.CheckConstraint(
                condition=Q(kind=UsageEntryKind.ADJUSTMENT)
                | Q(correction_of__isnull=True),
                name="subscription_correction_link_only_for_adjustment",
            ),
        ]

    def save(self, *args, **kwargs) -> None:
        if self.pk:
            raise ValidationError("Usage ledger is append-only")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Usage ledger is append-only")
