from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from hub_platform.subscriptions.keys import PlanCode


class BillingPeriod(models.TextChoices):
    MONTH = "MONTH", "Month"


class QuotaMode(models.TextChoices):
    HARD = "HARD", "Hard"
    SOFT = "SOFT", "Soft"
    RATE = "RATE", "Rate"
    CONCURRENT = "CONCURRENT", "Concurrent"
    UNLIMITED = "UNLIMITED", "Unlimited"


class QuotaLimitSource(models.TextChoices):
    FIXED = "FIXED", "Fixed"
    SUBSCRIPTION_AI_AGENT_QUANTITY = (
        "SUBSCRIPTION_AI_AGENT_QUANTITY",
        "Subscription AI agent quantity",
    )


class Plan(models.Model):
    code = models.CharField(max_length=32, choices=PlanCode.choices, unique=True)
    name = models.CharField(max_length=128)
    saleable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class PlanVersion(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    agent_unit_price_minor = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3, default="RUB")
    billing_period = models.CharField(
        max_length=16,
        choices=BillingPeriod.choices,
        default=BillingPeriod.MONTH,
    )
    fixed_ai_agent_quantity = models.PositiveIntegerField(null=True, blank=True)
    effective_from = models.DateTimeField(null=True, blank=True)
    transition_rules = models.JSONField(default=dict, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["plan__code", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "version"],
                name="uniq_subscription_plan_version",
            ),
            models.CheckConstraint(
                condition=Q(version__gt=0),
                name="subscription_plan_version_positive",
            ),
        ]

    @property
    def is_published(self) -> bool:
        return self.published_at is not None

    def save(self, *args, **kwargs) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk, published_at__isnull=False).exists():
            raise ValidationError("Published PlanVersion is immutable")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.published_at is not None:
            raise ValidationError("Published PlanVersion is immutable")
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.plan.code}:v{self.version}"


class EntitlementDefinition(models.Model):
    key = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=128)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key


class QuotaDefinition(models.Model):
    key = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    unit = models.CharField(max_length=32)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key


class PublishedVersionGrantModel(models.Model):
    class Meta:
        abstract = True

    def _assert_mutable(self) -> None:
        if self.plan_version_id and self.plan_version.published_at is not None:
            raise ValidationError("Grants of a published PlanVersion are immutable")

    def save(self, *args, **kwargs) -> None:
        self._assert_mutable()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._assert_mutable()
        return super().delete(*args, **kwargs)


class EntitlementGrant(PublishedVersionGrantModel):
    plan_version = models.ForeignKey(
        PlanVersion,
        on_delete=models.CASCADE,
        related_name="entitlement_grants",
    )
    definition = models.ForeignKey(
        EntitlementDefinition,
        on_delete=models.PROTECT,
        related_name="grants",
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plan_version", "definition"],
                name="uniq_plan_version_entitlement",
            )
        ]


class QuotaGrant(PublishedVersionGrantModel):
    plan_version = models.ForeignKey(
        PlanVersion,
        on_delete=models.CASCADE,
        related_name="quota_grants",
    )
    definition = models.ForeignKey(
        QuotaDefinition,
        on_delete=models.PROTECT,
        related_name="grants",
    )
    mode = models.CharField(max_length=16, choices=QuotaMode.choices)
    limit_source = models.CharField(
        max_length=48,
        choices=QuotaLimitSource.choices,
        default=QuotaLimitSource.FIXED,
    )
    limit_value = models.PositiveBigIntegerField(null=True, blank=True)
    window_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plan_version", "definition"],
                name="uniq_plan_version_quota",
            ),
            models.CheckConstraint(
                condition=(
                    Q(mode=QuotaMode.UNLIMITED, limit_value__isnull=True)
                    | Q(
                        limit_source=QuotaLimitSource.SUBSCRIPTION_AI_AGENT_QUANTITY,
                        limit_value__isnull=True,
                    )
                    | Q(
                        limit_source=QuotaLimitSource.FIXED,
                        limit_value__isnull=False,
                    )
                ),
                name="subscription_quota_limit_shape",
            ),
            models.CheckConstraint(
                condition=Q(mode=QuotaMode.RATE, window_seconds__isnull=False)
                | ~Q(mode=QuotaMode.RATE),
                name="subscription_rate_has_window",
            ),
        ]
