from __future__ import annotations

from django.db import models

from hub_platform.tenancy.models import TenantRelationModel


class UsageReservation(TenantRelationModel):
    """Lease on a concurrent quota (SPEC-HUB-0022 §7).

    A reservation holds a slot on a CONCURRENT-mode quota (e.g.
    ``concurrent_p2p_calls``) for the duration of a live session. It increments
    ``UsageCounter.reserved_value`` on acquire and decrements on release. A stale
    reservation (``expires_at`` in the past, ``released_at`` NULL) is reaped by the
    cleanup worker. The unique ``idempotency_key`` makes reserve/release idempotent.
    """

    period = models.ForeignKey(
        "subscriptions.UsagePeriod",
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    quota_definition = models.ForeignKey(
        "subscriptions.QuotaDefinition",
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    idempotency_key = models.CharField(max_length=160)
    aggregate_type = models.CharField(max_length=64, blank=True, default="")
    aggregate_id = models.CharField(max_length=128, blank=True, default="")
    source = models.CharField(max_length=128)
    quantity = models.PositiveBigIntegerField(default=1)
    acquired_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    released_at = models.DateTimeField(null=True, blank=True)

    tenant_relation_fields = ("period",)

    class Meta:
        ordering = ["-acquired_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"],
                name="uniq_concurrent_reservation_idempotency",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "quota_definition"]),
            models.Index(fields=["released_at", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.organization_id}:{self.quota_definition_id}:{self.idempotency_key}"

    @property
    def is_active(self) -> bool:
        return self.released_at is None
