from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.i18n import t
from chatballs.i18n.audience import customer_language
from chatballs.identity.audit import record_audit_event
from chatballs.identity.group_models import EmployeeGroup, EmployeeGroupMember
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    OrganizationStatus,
)
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic

# Приглашение существующего пользователя в организацию: письмо отправляет
# воркер по этому событию (identity.event_handlers).
MEMBERSHIP_INVITATION_REQUESTED = "identity.membership_invitation_requested"
# Приглашение владельца из платформенного провижининга (SPEC-HUB-0021 §8.2):
# учётной записи может ещё не быть, тогда человек создаёт её по ссылке.
OWNER_INVITATION_REQUESTED = "organization.owner_invitation_requested"
MEMBERSHIP_INVITATION_TTL = timedelta(days=7)


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
    position_title: str = "",
    phone: str = "",
    group_ids: list[int] | None = None,
) -> IssuedInvitation:
    normalized_email = email.strip().lower()
    now = timezone.now()
    # Повторное приглашение на тот же адрес заменяет прежнее: старое письмо
    # перестаёт работать, а не живёт параллельно с новым.
    OrganizationInvitation.objects.filter(
        organization=organization,
        email__iexact=normalized_email,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=now)
    token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation.objects.create(
        organization=organization,
        email=normalized_email,
        role=role,
        token_hash=_token_hash(token),
        expires_at=expires_at,
        created_by=created_by,
        position_title=position_title,
        phone=phone,
        group_ids=list(group_ids or []),
    )
    return IssuedInvitation(invitation=invitation, token=token)


def refresh_invitation_token(invitation: OrganizationInvitation) -> str:
    """Новый токен взамен прежнего.

    Открытый токен нигде не хранится, а письмо уходит из воркера позже, чем
    приглашение выписано, — поэтому воркер выпускает токен сам, в момент
    отправки, и старый перестаёт действовать.
    """

    token = secrets.token_urlsafe(32)
    invitation.token_hash = _token_hash(token)
    invitation.save(update_fields=["token_hash"])
    return token


def invite_existing_user(
    *,
    organization: Organization,
    user: HumanUser,
    role: str,
    position_title: str,
    phone: str,
    groups: list[EmployeeGroup],
    created_by: OrganizationMembership | None,
    context: TenantContext,
    request=None,
) -> OrganizationInvitation:
    """Пригласить уже существующую учётную запись в организацию.

    Учётная запись глобальная, а членство появляется только с согласия
    человека: он получает письмо и принимает приглашение под своим входом.
    """

    issued = issue_invitation(
        organization=organization,
        email=user.email,
        role=role,
        expires_at=timezone.now() + MEMBERSHIP_INVITATION_TTL,
        created_by=created_by,
        position_title=position_title,
        phone=phone,
        group_ids=[group.id for group in groups],
    )
    record_audit_event(
        action="identity.employee_invited",
        actor=context.actor_user,
        organization=organization,
        object_type="OrganizationInvitation",
        object_id=str(issued.invitation.id),
        payload={"role": role},
        request=request,
    )
    enqueue_event(
        DomainEvent(
            aggregate_type="OrganizationInvitation",
            aggregate_id=str(issued.invitation.id),
            event_type=MEMBERSHIP_INVITATION_REQUESTED,
            payload={"invitationId": issued.invitation.id},
            tenant_context=context,
        )
    )
    return issued.invitation


def invitation_preview(token: str) -> dict[str, object] | None:
    """Что видит человек по ссылке до входа: куда зовут и есть ли учётная запись."""

    invitation = pending_invitation_for_token(token)
    if invitation is None:
        return None
    return {
        "email": invitation.email,
        "organizationName": invitation.organization.name,
        "accountExists": HumanUser.objects.filter(email__iexact=invitation.email).exists(),
    }


@transaction.atomic
def register_and_accept(*, token: str, full_name: str, password: str) -> AcceptedInvitation:
    """Создать учётную запись по приглашению и сразу принять его.

    Только для адреса без учётной записи: у существующей есть пароль, и
    приглашение принимается после входа. Пароль проверяется теми же
    правилами, что в мастере первого запуска.
    """

    invitation = pending_invitation_for_token(token)
    if invitation is None:
        raise InvitationError(t("identity.invitation_invalid"), code="invitation_invalid")
    if HumanUser.objects.filter(email__iexact=invitation.email).exists():
        raise InvitationError(t("identity.invitation_account_exists"), code="account_exists")
    name = " ".join(full_name.split())
    if not name:
        raise ValidationError({"fullName": t("setup.your_name_required")})
    probe = HumanUser(email=invitation.email, full_name=name)
    validate_password(password, user=probe)
    user = HumanUser.objects.create_user(
        email=invitation.email,
        password=password,
        full_name=name,
        is_staff=False,
        is_superuser=False,
        must_change_password=False,
    )
    return accept_invitation(token=token, user=user)


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
    """Принять приглашение: владельца (SPEC-HUB-0021 §8.2) или сотрудника.

    Членство собирается из полей приглашения; для владельца организация ещё
    и активируется. Идемпотентно: повторное принятие того же токена не создаёт
    второго членства. Нужна учётная запись с тем же e-mail.
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
        membership = _ensure_membership(organization, user, invitation)
        if invitation.role == EmployeeRole.OWNER:
            _activate_organization(organization, user, membership)
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at"])
        record_audit_event(
            action=(
                "organization.owner_activated"
                if invitation.role == EmployeeRole.OWNER
                else "identity.invitation_accepted"
            ),
            actor=user,
            organization=organization,
            object_type="OrganizationInvitation",
            object_id=str(invitation.id),
            payload={"role": invitation.role},
        )
    return AcceptedInvitation(
        invitation=invitation, membership=membership, organization=organization
    )


def _ensure_membership(
    organization: Organization, user: HumanUser, invitation: OrganizationInvitation
) -> OrganizationMembership:
    position_title = invitation.position_title
    if not position_title and invitation.role == EmployeeRole.OWNER:
        position_title = t("setup.owner_position", language=customer_language(organization))
    membership, created = OrganizationMembership.objects.get_or_create(
        user=user,
        organization=organization,
        defaults={
            "role": invitation.role,
            "position_title": position_title,
            "phone": invitation.phone,
            "totp_required": False,
        },
    )
    if membership.role != invitation.role:
        # Уже существующее членство с другой ролью приглашение молча не меняет:
        # это конфликт, а не повышение.
        raise InvitationError(
            t("identity.role_conflict"),
            code="role_conflict",
        )
    if created and invitation.group_ids:
        # Группы, которые к моменту принятия ещё существуют.
        groups = EmployeeGroup.objects.filter(
            organization=organization, id__in=list(invitation.group_ids)
        )
        EmployeeGroupMember.objects.bulk_create(
            [
                EmployeeGroupMember(
                    organization_id=organization.id, group=group, employee=membership
                )
                for group in groups
            ]
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
