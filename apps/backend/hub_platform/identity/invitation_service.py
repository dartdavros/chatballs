from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from hub_platform.identity.models import (
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class IssuedInvitation:
    invitation: OrganizationInvitation
    token: str


@transaction.atomic
def issue_invitation(
    *,
    organization: Organization,
    email: str,
    role: str,
    expires_at: datetime,
    created_by: OrganizationMembership | None,
) -> IssuedInvitation:
    normalized_email = email.strip().lower()
    now = timezone.now()
    OrganizationInvitation.objects.filter(
        organization=organization,
        email__iexact=normalized_email,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__lte=now,
    ).update(revoked_at=now)
    token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation.objects.create(
        organization=organization,
        email=normalized_email,
        role=role,
        token_hash=_token_hash(token),
        expires_at=expires_at,
        created_by=created_by,
    )
    return IssuedInvitation(invitation=invitation, token=token)


def pending_invitation_for_token(token: str) -> OrganizationInvitation | None:
    if not token:
        return None
    return OrganizationInvitation.objects.filter(
        token_hash=_token_hash(token),
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).first()
