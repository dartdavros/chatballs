from __future__ import annotations

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from chatballs.ai.knowledge_categories import ensure_uncategorized_category
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.i18n import t
from chatballs.i18n.audience import customer_language
from chatballs.identity.audit import record_audit_event
from chatballs.identity.invitation_service import issue_invitation
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
    OrganizationStatus,
)
from chatballs.platform.errors import (
    ProvisioningConflict,
    ProvisioningOwnerUnavailable,
    ProvisioningValidation,
)
from chatballs.platform.models import (
    OrganizationProvisioning,
    PlatformOperator,
    ProvisioningStatus,
)
from chatballs.platform.provisioning_command import (
    ProvisioningCommand,
    ProvisioningResult,
    is_replay,
    is_terminal,
)
from chatballs.tenancy.context import TenantActorKind, TenantContext
from chatballs.tenancy.database import tenant_atomic

OWNER_INVITATION_TTL = timedelta(days=7)


def provision_organization(
    *,
    command: ProvisioningCommand,
    operator: PlatformOperator,
) -> ProvisioningResult:
    """Single write boundary for tenant provisioning (SPEC-HUB-0021 §4).

    Coordinates identity, audit and outbox in one
    transaction (тариф удалён, ADR-CHATBALLS-0042 §2: организация создаётся без подписки). Tenant-owned rows are written under set_local_tenant(new_org.id)
    via tenant_atomic. No email/provider calls happen before commit (SPEC §4).
    """
    with transaction.atomic():
        return _run(command, operator)


def _run(command: ProvisioningCommand, operator: PlatformOperator) -> ProvisioningResult:
    _validate_command(command)

    existing = OrganizationProvisioning.objects.filter(
        idempotency_key=command.idempotency_key
    ).first()
    if existing is not None:
        if is_terminal(existing) and is_replay(existing, command):
            return ProvisioningResult(
                provisioning=existing,
                organization=existing.organization,
                created=False,
            )
        if is_terminal(existing) and not is_replay(existing, command):
            raise ProvisioningConflict(
                "Idempotency key was used for a different request", code="idempotency_conflict"
            )
        # Non-terminal record from a FAILED prior attempt -> retry on same record.

    provisioning = _open_or_resume(existing, command, operator)
    try:
        owner_user = _resolve_owner_user(command.owner_email)
        org = _create_organization(command, owner_user)
        provisioning.organization = org
        provisioning.save(update_fields=["organization"])

        with tenant_atomic(org.id):
            ensure_uncategorized_category(org)
            context = TenantContext.for_resource(
                org,
                actor_kind=TenantActorKind.SYSTEM,
                actor_user=owner_user,
            )
            if owner_user is not None and owner_user.is_active:
                _provision_active_owner(org, owner_user, command, context)
                provisioning.status = ProvisioningStatus.COMPLETED
            else:
                _provision_pending_owner(org, owner_user, command, context)
                provisioning.status = ProvisioningStatus.WAITING_FOR_OWNER

        provisioning.failure_code = ""
        provisioning.failure_details_safe = ""
        provisioning.save(update_fields=["status", "failure_code", "failure_details_safe"])
        return ProvisioningResult(provisioning=provisioning, organization=org, created=True)
    except Exception as error:  # noqa: BLE001 - record failure then re-raise to rollback
        provisioning.status = ProvisioningStatus.FAILED
        provisioning.failure_code = type(error).__name__
        provisioning.failure_details_safe = _safe_message(error)
        provisioning.save(update_fields=["status", "failure_code", "failure_details_safe"])
        raise


def _validate_command(command: ProvisioningCommand) -> None:
    if not command.organization_name.strip():
        raise ProvisioningValidation("organization_name is required", code="name_required")
    if not command.organization_slug.strip():
        raise ProvisioningValidation("organization_slug is required", code="slug_required")
    if not command.owner_email.strip():
        raise ProvisioningValidation("owner_email is required", code="email_required")


def _open_or_resume(
    existing: OrganizationProvisioning | None,
    command: ProvisioningCommand,
    operator: PlatformOperator,
) -> OrganizationProvisioning:
    if existing is not None:
        existing.status = ProvisioningStatus.IN_PROGRESS
        existing.request_hash = command.request_hash()
        existing.save(update_fields=["status", "request_hash", "updated_at"])
        return existing
    return OrganizationProvisioning.objects.create(
        idempotency_key=command.idempotency_key,
        request_hash=command.request_hash(),
        source=command.source,
        requested_by=operator,
        status=ProvisioningStatus.IN_PROGRESS,
    )


def _resolve_owner_user(email: str) -> HumanUser | None:
    normalized = HumanUser.objects.normalize_email(email)
    user = HumanUser.objects.filter(email__iexact=normalized).first()
    if user is None:
        return None
    if not user.is_active:
        raise ProvisioningOwnerUnavailable(
            "Existing owner account is globally unavailable", code="owner_inactive"
        )
    return user


def _create_organization(
    command: ProvisioningCommand, owner_user: HumanUser | None
) -> Organization:
    active = owner_user is not None and owner_user.is_active
    try:
        org = Organization.objects.create(
            name=command.organization_name.strip(),
            slug=command.organization_slug.strip(),
            status=OrganizationStatus.ACTIVE if active else OrganizationStatus.PENDING_OWNER,
            timezone=command.timezone,
            currency=command.currency.upper(),
        )
    except ValidationError as error:
        raise ProvisioningValidation(str(error), code="organization_invalid") from error
    return org


def _provision_active_owner(
    org: Organization,
    owner_user: HumanUser,
    command: ProvisioningCommand,
    context: TenantContext,
) -> None:
    OrganizationMembership.objects.create(
        user=owner_user,
        organization=org,
        role=EmployeeRole.OWNER,
        position_title=_owner_position_title(org),
    )
    record_audit_event(
        action="organization.provisioned",
        actor=owner_user,
        organization=org,
        object_type="Organization",
        object_id=str(org.public_id),
        payload={"source": command.source},
    )
    enqueue_event(
        DomainEvent(
            aggregate_type="Organization",
            aggregate_id=str(org.public_id),
            event_type="organization.provisioned",
            payload={},
            tenant_context=context,
        )
    )


def _provision_pending_owner(
    org: Organization,
    owner_user: HumanUser | None,
    command: ProvisioningCommand,
    context: TenantContext,
) -> None:
    # No password/dummy user is created (SPEC-HUB-0021 §8.2). An OWNER invitation
    # is issued; the organization stays PENDING_OWNER until it is accepted.
    issued = issue_invitation(
        organization=org,
        email=command.owner_email,
        role=EmployeeRole.OWNER,
        expires_at=timezone.now() + OWNER_INVITATION_TTL,
        created_by=None,
    )
    record_audit_event(
        action="organization.owner_invitation_requested",
        actor=owner_user,
        organization=org,
        object_type="Organization",
        object_id=str(org.public_id),
        payload={"source": command.source},
    )
    enqueue_event(
        DomainEvent(
            aggregate_type="Organization",
            aggregate_id=str(org.public_id),
            event_type="organization.owner_invitation_requested",
            payload={"invitationId": str(issued.invitation.id)},
            tenant_context=context,
        )
    )


def _owner_position_title(org: Organization) -> str:
    # Должность хранится текстом, поэтому пишется сразу на языке организации,
    # а не оператора платформы: переводить её потом будет нечем.
    return t("setup.owner_position", language=customer_language(org))


def _safe_message(error: Exception) -> str:
    text = str(error).strip()
    # Keep failure details free of secrets; class name + a short, non-verbose text.
    return text[:200] if text else type(error).__name__
