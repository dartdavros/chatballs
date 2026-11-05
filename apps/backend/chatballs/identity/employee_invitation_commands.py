"""Invitation lifecycle with original role checks, audit and transactional outbox."""

from django.db import transaction
from django.utils import timezone

from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.employee_invitation_queries import _pending
from chatballs.identity.employee_outcomes import EmployeeOutcome, rejected
from chatballs.identity.governance import can_create_role
from chatballs.identity.invitation_service import (
    MEMBERSHIP_INVITATION_REQUESTED,
    MEMBERSHIP_INVITATION_TTL,
)
from chatballs.identity.policy import has_capability_any_scope


def _load(context, invitation_id):
    actor = context.membership
    if not has_capability_any_scope(actor, "employees.manage"):
        return rejected(t("admin.not_allowed"), "forbidden")
    invitation = _pending(context.organization_id).select_for_update().filter(pk=invitation_id).first()
    if invitation is None:
        return rejected(t("identity.invitation_invalid"), "not_found")
    if not can_create_role(actor, invitation.role):
        return rejected(t("admin.not_allowed"), "forbidden")
    return invitation


@transaction.atomic
def resend(context, invitation_id, *, request=None):
    invitation = _load(context, invitation_id)
    if isinstance(invitation, EmployeeOutcome):
        return invitation
    invitation.expires_at = timezone.now() + MEMBERSHIP_INVITATION_TTL
    invitation.save(update_fields=["expires_at"])
    record_audit_event(action="identity.employee_invited", actor=context.actor_user,
        organization=invitation.organization, object_type="OrganizationInvitation",
        object_id=str(invitation.id), payload={"role": invitation.role, "resend": True}, request=request)
    enqueue_event(DomainEvent(aggregate_type="OrganizationInvitation", aggregate_id=str(invitation.id),
        event_type=MEMBERSHIP_INVITATION_REQUESTED, payload={"invitationId": invitation.id},
        tenant_context=context))
    return EmployeeOutcome({"ok": True})


@transaction.atomic
def revoke(context, invitation_id, *, request=None):
    invitation = _load(context, invitation_id)
    if isinstance(invitation, EmployeeOutcome):
        return invitation
    invitation.revoked_at = timezone.now()
    invitation.save(update_fields=["revoked_at"])
    record_audit_event(action="identity.invitation_revoked", actor=context.actor_user,
        organization=invitation.organization, object_type="OrganizationInvitation",
        object_id=str(invitation.id), payload={"role": invitation.role}, request=request)
    return EmployeeOutcome({"ok": True})
