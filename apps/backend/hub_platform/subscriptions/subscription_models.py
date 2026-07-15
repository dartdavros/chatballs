from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class SubscriptionStatus(models.TextChoices):
    PENDING_PAYMENT = "PENDING_PAYMENT", "Pending payment"
    ACTIVE = "ACTIVE", "Active"
    GRACE_PERIOD = "GRACE_PERIOD", "Grace period"
    SUSPENDED = "SUSPENDED", "Suspended"
    CANCELLED = "CANCELLED", "Cancelled"


class OverrideTarget(models.TextChoices):
    ENTITLEMENT = "ENTITLEMENT", "Entitlement"
    QUOTA = "QUOTA", "Quota"


class OverrideOperation(models.TextChoices):
    ENABLE = "ENABLE", "Enable"
    DISABLE = "DISABLE", "Disable"
    SET = "SET", "Set"
    ADD = "ADD", "Add"


class Subscription(models.Model):
    organization = models.OneToOneField(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="subscription",
    )
    plan_version = models.ForeignKey(
        "subscriptions.PlanVersion",
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    ai_agent_quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=32,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING_PAYMENT,
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    pending_plan_version = models.ForeignKey(
        "subscriptions.PlanVersion",
        on_delete=models.PROTECT,
        related_name="pending_subscriptions",
        null=True,
        blank=True,
    )
    pending_ai_agent_quantity = models.PositiveIntegerField(null=True, blank=True)
    suspension_reason = models.CharField(max_length=64, blank=True)
    lifecycle_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(ai_agent_quantity__gt=0),
                name="subscription_ai_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(pending_ai_agent_quantity__isnull=True)
                | Q(pending_ai_agent_quantity__gt=0),
                name="subscription_pending_ai_quantity_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(current_period_start__isnull=True, current_period_end__isnull=True)
                    | Q(current_period_start__isnull=False, current_period_end__isnull=False)
                ),
                name="subscription_period_bounds_together",
            ),
        ]

    def clean(self) -> None:
        fixed_quantity = self.plan_version.fixed_ai_agent_quantity
        if fixed_quantity is not None and self.ai_agent_quantity != fixed_quantity:
            raise ValidationError(
                {"ai_agent_quantity": f"This plan version requires quantity {fixed_quantity}"}
            )
        if (
            self.current_period_start is not None
            and self.current_period_end is not None
            and self.current_period_start >= self.current_period_end
        ):
            raise ValidationError({"current_period_end": "Period end must follow start"})

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.plan_version}"

    @property
    def monthly_charge_minor(self) -> int:
        return self.plan_version.agent_unit_price_minor * self.ai_agent_quantity


class SubscriptionOverride(models.Model):
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="subscription_overrides",
    )
    target = models.CharField(max_length=16, choices=OverrideTarget.choices)
    entitlement_definition = models.ForeignKey(
        "subscriptions.EntitlementDefinition",
        on_delete=models.PROTECT,
        related_name="overrides",
        null=True,
        blank=True,
    )
    quota_definition = models.ForeignKey(
        "subscriptions.QuotaDefinition",
        on_delete=models.PROTECT,
        related_name="overrides",
        null=True,
        blank=True,
    )
    operation = models.CharField(max_length=16, choices=OverrideOperation.choices)
    value = models.BigIntegerField(null=True, blank=True)
    reason = models.TextField()
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="subscription_overrides_created",
    )
    correlation_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["organization", "starts_at", "ends_at"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        target=OverrideTarget.ENTITLEMENT,
                        entitlement_definition__isnull=False,
                        quota_definition__isnull=True,
                        operation__in=[OverrideOperation.ENABLE, OverrideOperation.DISABLE],
                        value__isnull=True,
                    )
                    | Q(
                        target=OverrideTarget.QUOTA,
                        entitlement_definition__isnull=True,
                        quota_definition__isnull=False,
                        operation__in=[OverrideOperation.SET, OverrideOperation.ADD],
                        value__isnull=False,
                    )
                ),
                name="subscription_override_shape",
            ),
            models.CheckConstraint(
                condition=Q(ends_at__isnull=True) | Q(ends_at__gt=models.F("starts_at")),
                name="subscription_override_valid_window",
            ),
        ]

    def clean(self) -> None:
        if self.target == OverrideTarget.QUOTA and self.operation == OverrideOperation.SET:
            if self.value is not None and self.value < 0:
                raise ValidationError({"value": "Quota override cannot set a negative limit"})

    @property
    def key(self) -> str:
        if self.entitlement_definition_id:
            return self.entitlement_definition.key
        return self.quota_definition.key
