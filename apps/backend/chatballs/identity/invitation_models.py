from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from chatballs.identity.models import EmployeeRole, Organization, OrganizationMembership


class OrganizationInvitation(models.Model):
    """One-time membership invitation; plaintext tokens and passwords are never stored."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="invitations",
    )
    email = models.EmailField()
    role = models.CharField(max_length=32, choices=EmployeeRole.choices)
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(
        OrganizationMembership,
        on_delete=models.PROTECT,
        related_name="invitations_created",
        null=True,
        blank=True,
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                "organization",
                condition=Q(accepted_at__isnull=True, revoked_at__isnull=True),
                name="uniq_pending_invitation_org_email",
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.email}:{self.role}"

    def save(self, *args, **kwargs) -> None:
        self.email = self.email.strip().lower()
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        if self.created_by_id and self.created_by.organization_id != self.organization_id:
            raise ValidationError("Invitation creator must belong to the same organization")
        if self._state.adding and self.expires_at <= timezone.now():
            raise ValidationError({"expires_at": "Invitation expiry must be in the future"})

    @property
    def is_pending(self) -> bool:
        return (
            self.accepted_at is None
            and self.revoked_at is None
            and self.expires_at > timezone.now()
        )
