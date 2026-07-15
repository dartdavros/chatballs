from __future__ import annotations

from django.db import models


class PlatformOperator(models.Model):
    """Global platform principal (ADR-HUB-0031 §9). Not derived from tenant
    membership; never becomes an Organization OWNER. Authenticated via
    PlatformToken (machine-to-machine)."""

    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PlatformToken(models.Model):
    """Opaque API token stored as a sha256 hash (mirror identity invitation tokens).
    Plaintext is returned only once at creation time by the token service."""

    operator = models.ForeignKey(
        PlatformOperator,
        on_delete=models.CASCADE,
        related_name="tokens",
    )
    name = models.CharField(max_length=128)
    token_hash = models.CharField(max_length=128, unique=True)
    capabilities = models.JSONField(default=list, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(token_hash__isnull=False) & ~models.Q(token_hash=""),
                name="platform_token_hash_present",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.operator.name}:{self.name}"

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None
