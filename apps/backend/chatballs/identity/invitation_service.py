from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    OrganizationStatus,
)
from chatballs.tenancy.database import tenant_atomic


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class IssuedInvitation:
    invitation: OrganizationInvitation
    token: str


@dataclass(frozen=True, slots=True)
class AcceptedInvitation:
    invitation: OrganizationInvitation
    membership: OrganizationMembership
    organization: Organization


class InvitationError(Exception):
    """Safe-to-expose invitation accept error."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


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


@transaction.atomic
def accept_invitation(*, token: str, user: HumanUser) -> AcceptedInvitation:
    """Accept an OWNER invitation and activate the organization (SPEC-HUB-0021 §8.2).

    Idempotent: re-accepting the same token does not create a second membership
    or usage period. Requires an authenticated HumanUser with a matching email.
    """
    invitation = pending_invitation_for_token(token)
    if invitation is None:
        already = _already_accepted_for(token, user)
        if already is not None:
            return already
        raise InvitationError(
            t("identity.invitation_invalid"), code="invitation_invalid"
        )
    normalized_email = user.email.strip().lower()
    if invitation.email.strip().lower() != normalized_email:
        raise InvitationError(
            t("identity.invitation_email_mismatch"), code="email_mismatch"
        )

    organization = invitation.organization
    with tenant_atomic(organization.id):
        membership = _ensure_owner_membership(organization, user)
        if invitation.role == EmployeeRole.OWNER:
            _activate_organization(organization, user, membership)
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at"])
        record_audit_event(
            action="organization.owner_activated",
            actor=user,
            organization=organization,
            object_type="OrganizationInvitation",
            object_id=str(invitation.id),
            payload={"role": invitation.role},
        )
    return AcceptedInvitation(
        invitation=invitation, membership=membership, organization=organization
    )


def _ensure_owner_membership(
    organization: Organization, user: HumanUser
) -> OrganizationMembership:
    membership, _ = OrganizationMembership.objects.get_or_create(
        user=user,
        organization=organization,
        defaults={
            "role": EmployeeRole.OWNER,
            "position_title": "Владелец",
            "totp_required": False,
        },
    )
    if membership.role != EmployeeRole.OWNER:
        # An existing non-OWNER membership for this user should not be silently
        # promoted by an invitation; surface as a conflict instead.
        raise InvitationError(
            t("identity.role_conflict"),
            code="role_conflict",
        )
    return membership


def _activate_organization(
    organization: Organization,
    user: HumanUser,
    membership: OrganizationMembership,
) -> None:
    if organization.status != OrganizationStatus.ACTIVE:
        organization.status = OrganizationStatus.ACTIVE
        organization.save(update_fields=["status"])


def _already_accepted_for(
    token: str, user: HumanUser
) -> AcceptedInvitation | None:
    """Idempotent re-accept: if this token was already accepted by the same user,
    return the existing result instead of raising (SPEC-HUB-0021 §11/§15)."""
    invitation = OrganizationInvitation.objects.filter(
        token_hash=_token_hash(token),
        accepted_at__isnull=False,
        revoked_at__isnull=True,
    ).first()
    if invitation is None:
        return None
    membership = OrganizationMembership.objects.filter(
        user=user, organization=invitation.organization
    ).first()
    if membership is None:
        return None
    return AcceptedInvitation(
        invitation=invitation, membership=membership, organization=invitation.organization
    )
