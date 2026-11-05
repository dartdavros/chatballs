"""Original widget call operations, sharing the normal call lifecycle."""

from django.db import transaction
from django.utils import timezone

from chatballs.calls.errors import CallConflict, CallInvalidTransition, CallTokenError
from chatballs.calls.lifecycle import transition_call
from chatballs.calls.models import (
    UNFINISHED_CALL_STATUSES,
    CallEndedBy,
    CallInvite,
    CallSession,
    CallStatus,
    ParticipantSide,
)
from chatballs.calls.public_access import ResolvedInvite
from chatballs.calls.tokens import issue_call_access_token
from chatballs.conversations.models import ConnectionIdentity
from chatballs.i18n import t


def webchat_active_call(identity: ConnectionIdentity) -> CallSession | None:
    return (
        CallSession.objects.filter(
            invite__connection_identity=identity,
            status__in=UNFINISHED_CALL_STATUSES,
        )
        .select_related("invite", "initiated_by")
        .first()
    )


@transaction.atomic
def open_call_for_identity(*, identity: ConnectionIdentity) -> ResolvedInvite:
    call = webchat_active_call(identity)
    if call is None:
        raise CallTokenError(t("webchat.no_active_invite"))
    invite = CallInvite.objects.select_for_update().get(call_session=call)
    if invite.expires_at <= timezone.now():
        raise CallTokenError(t("webchat.no_active_invite"))
    if invite.opened_at is None:
        invite.opened_at = timezone.now()
        invite.save(update_fields=["opened_at"])
    access_token = issue_call_access_token(
        call_session_id=call.id,
        side=ParticipantSide.CUSTOMER,
        subject_id=str(invite.id),
    )
    return ResolvedInvite(invite=invite, customer_access_token=access_token)


def decline_call_for_identity(*, identity: ConnectionIdentity, expected_conversation_id=None) -> CallSession:
    call = webchat_active_call(identity)
    if call is None:
        raise CallTokenError(t("webchat.no_active_invite"))
    if expected_conversation_id is not None and call.conversation_id != expected_conversation_id:
        raise CallTokenError(t("calls.token_invalid"))
    try:
        return transition_call(
            call_session_id=call.id,
            target_status=CallStatus.DECLINED,
            ended_by=CallEndedBy.CUSTOMER,
        )
    except CallInvalidTransition as error:
        raise CallConflict(t("calls.invite_cannot_decline")) from error
