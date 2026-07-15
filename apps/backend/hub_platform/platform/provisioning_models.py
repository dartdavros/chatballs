from __future__ import annotations

from django.db import models

from hub_platform.platform.operator_models import PlatformOperator


class ProvisioningSource(models.TextChoices):
    PLATFORM_OPERATOR = "PLATFORM_OPERATOR", "Platform operator"
    SELF_SERVICE = "SELF_SERVICE", "Self-service"
    SELF_HOSTED_SETUP = "SELF_HOSTED_SETUP", "Self-hosted setup"
    MIGRATION = "MIGRATION", "Migration"


class ProvisioningStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    WAITING_FOR_OWNER = "WAITING_FOR_OWNER", "Waiting for owner"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class OrganizationProvisioning(models.Model):
    """Platform-owned process record (SPEC-HUB-0021 §6). Idempotency key is
    globally unique; the same key + payload returns the existing result, while a
    differing payload is a conflict. failure_details_safe must never contain
    secrets, tokens or provider credentials (SPEC-HUB-0021 §6/§13)."""

    idempotency_key = models.CharField(max_length=160, unique=True)
    request_hash = models.CharField(max_length=128)
    source = models.CharField(max_length=32, choices=ProvisioningSource.choices)
    requested_by = models.ForeignKey(
        PlatformOperator,
        on_delete=models.PROTECT,
        related_name="provisioning_requests",
    )
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="provisioning_records",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=32,
        choices=ProvisioningStatus.choices,
        default=ProvisioningStatus.PENDING,
    )
    failure_code = models.CharField(max_length=64, blank=True, default="")
    failure_details_safe = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "updated_at"]),
            models.Index(fields=["source", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.idempotency_key}:{self.status}"
