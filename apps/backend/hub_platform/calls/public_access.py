from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from hub_platform.calls.errors import (
    CallAccessDenied,
    CallConflict,
    CallInvalidTransition,
    CallTokenError,
)
from hub_platform.calls.lifecycle import transition_call
from hub_platform.calls.models import (
    TERMINAL_CALL_STATUSES,
    CallEndedBy,
    CallInvite,
    CallSession,
    CallStatus,
    ParticipantSide,
)
from hub_platform.calls.permissions import ensure_call_access
from hub_platform.calls.tokens import (
    CallAccessClaims,
    hash_invite_token,
    issue_call_access_token,
    verify_call_access_token,
)
from hub_platform.identity.models import Organization, OrganizationMembership
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.database import tenant_atomic
from hub_platform.tenancy.ingress import call_invite_route, call_session_route


@dataclass(frozen=True)
class ResolvedInvite:
    invite: CallInvite
    customer_access_token: str


def resolve_invite(*, token: str) -> ResolvedInvite:
    message = "Недействительное или истёкшее приглашение"
    token_hash = hash_invite_token(token)
    route = call_invite_route(token_hash)
    if route is None:
        raise CallTokenError(message)
    try:
        organization = Organization.objects.get(pk=route.organization_id)
    except Organization.DoesNotExist:
        raise CallTokenError(message) from None
    context = TenantContext.for_resource(organization)
    with tenant_atomic(context):
        invite = (
            CallInvite.objects.select_for_update()
            .select_related(
                "call_session",
                "call_session__initiated_by",
                "connection_identity",
            )
            .filter(
                id=route.resource_id,
                organization=organization,
                token_hash=token_hash,
            )
            .first()
        )
        now = timezone.now()
        if (
            invite is None
            or invite.expires_at <= now
            or invite.opened_at is not None
            or invite.call_session.status in TERMINAL_CALL_STATUSES
        ):
            raise CallTokenError(message)
        invite.opened_at = now
        invite.save(update_fields=["opened_at"])
        access_token = issue_call_access_token(
            call_session_id=invite.call_session_id,
            side=ParticipantSide.CUSTOMER,
            subject_id=str(invite.id),
        )
        return ResolvedInvite(invite=invite, customer_access_token=access_token)


def _authorize_call_access(
    *,
    token: str,
    allow_terminal: bool = False,
) -> tuple[CallAccessClaims, CallSession, TenantContext]:
    claims = verify_call_access_token(token)
    route = call_session_route(str(claims.call_session_id))
    if route is None:
        raise CallTokenError("Недействительный или истёкший call access token")
    try:
        organization = Organization.objects.get(pk=route.organization_id)
    except Organization.DoesNotExist:
        raise CallTokenError("Недействительный или истёкший call access token") from None
    resource_context = TenantContext.for_resource(organization)
    with tenant_atomic(resource_context):
        try:
            call = CallSession.objects.select_related(
                "conversation", "conversation__channel", "initiated_by", "organization"
            ).get(id=claims.call_session_id, organization=organization)
        except CallSession.DoesNotExist:
            raise CallTokenError("Недействительный или истёкший call access token") from None
        if call.status in TERMINAL_CALL_STATUSES and not allow_terminal:
            raise CallTokenError("Звонок уже завершён")
        membership = None
        if claims.side == ParticipantSide.STAFF:
            participant = call.participants.select_related("user").filter(
                side=ParticipantSide.STAFF,
                user_id=claims.subject_id,
            ).first()
            valid = participant is not None
            if participant is not None:
                membership = OrganizationMembership.objects.select_related("user").filter(
                    user=participant.user,
                    organization=organization,
                    blocked_at__isnull=True,
                ).first()
                try:
                    ensure_call_access(user=membership, call_session=call)
                except CallAccessDenied:
                    valid = False
        else:
            invite = CallInvite.objects.filter(
                id=claims.subject_id,
                call_session=call,
                organization=organization,
            ).first()
            valid = invite is not None and (
                invite.expires_at > timezone.now()
                or call.status not in {CallStatus.REQUESTED, CallStatus.RINGING}
            )
        if not valid:
            raise CallTokenError("Недействительный или истёкший call access token")
        context = (
            TenantContext.for_membership(membership)
            if membership is not None
            else resource_context
        )
        return claims, call, context


def authorize_call_access_token(
    *,
    token: str,
    allow_terminal: bool = False,
) -> tuple[CallAccessClaims, CallSession]:
    claims, call, _context = _authorize_call_access(
        token=token,
        allow_terminal=allow_terminal,
    )
    return claims, call


def authorize_call_access_context(
    *, token: str, allow_terminal: bool = False
) -> tuple[CallAccessClaims, CallSession, TenantContext]:
    return _authorize_call_access(token=token, allow_terminal=allow_terminal)


def _customer_call(
    *,
    token: str,
    allow_terminal: bool = False,
) -> tuple[CallSession, TenantContext]:
    claims, call, context = _authorize_call_access(
        token=token,
        allow_terminal=allow_terminal,
    )
    if claims.side != ParticipantSide.CUSTOMER:
        raise CallTokenError("Недействительный или истёкший call access token")
    return call, context


def accept_call_by_access_token(*, token: str) -> CallSession:
    call, context = _customer_call(token=token)
    with tenant_atomic(context):
        try:
            if call.status == CallStatus.REQUESTED:
                call = transition_call(call_session_id=call.id, target_status=CallStatus.RINGING)
            transition_call(call_session_id=call.id, target_status=CallStatus.ACCEPTED)
            return CallSession.objects.select_related("initiated_by").get(
                id=call.id,
                organization=context.organization,
            )
        except CallInvalidTransition as error:
            raise CallConflict("Приглашение уже нельзя принять") from error


def decline_call_by_access_token(*, token: str) -> CallSession:
    call, context = _customer_call(token=token, allow_terminal=True)
    with tenant_atomic(context):
        if call.status == CallStatus.DECLINED:
            return call
        try:
            transition_call(
                call_session_id=call.id,
                target_status=CallStatus.DECLINED,
                ended_by=CallEndedBy.CUSTOMER,
            )
            return CallSession.objects.select_related("initiated_by").get(
                id=call.id,
                organization=context.organization,
            )
        except CallInvalidTransition as error:
            raise CallConflict("Приглашение уже нельзя отклонить") from error


def call_state_by_access_token(*, token: str) -> CallSession:
    _claims, call, context = _authorize_call_access(token=token, allow_terminal=True)
    with tenant_atomic(context):
        return CallSession.objects.select_related("initiated_by").get(
            id=call.id,
            organization=context.organization,
        )
