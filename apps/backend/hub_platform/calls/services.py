from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from hub_platform.calls.errors import CallConflict, CallTokenError
from hub_platform.calls.models import (
    CallInvite,
    CallParticipant,
    CallSession,
    CallStatus,
    ParticipantSide,
    TERMINAL_CALL_STATUSES,
    UNFINISHED_CALL_STATUSES,
)
from hub_platform.calls.permissions import ensure_call_access, ensure_conversation_call_access
from hub_platform.calls.tokens import (
    CallAccessClaims,
    hash_invite_token,
    issue_call_access_token,
    issue_invite_token,
    verify_call_access_token,
)
from hub_platform.conversations.models import (
    ConnectionIdentity,
    Conversation,
    ControlMode,
    LifecycleState,
)
from hub_platform.conversations.services import ClaimError, claim_locked_conversation


@dataclass(frozen=True)
class CreatedCall:
    call_session: CallSession
    invite_token: str
    staff_access_token: str


@dataclass(frozen=True)
class ResolvedInvite:
    invite: CallInvite
    customer_access_token: str


def _conversation_identity(conversation: Conversation) -> ConnectionIdentity:
    if conversation.contact_id is None or conversation.connection_id is None:
        raise CallConflict("У диалога нет клиентской identity для звонка")
    identities = list(
        ConnectionIdentity.objects.filter(
            contact_id=conversation.contact_id,
            connection_id=conversation.connection_id,
        )
        .order_by("id")[:2]
    )
    if len(identities) != 1:
        raise CallConflict("Клиентская identity звонка отсутствует или неоднозначна")
    return identities[0]


def _check_call_creation_conflicts(*, conversation: Conversation, initiator) -> None:
    if conversation.lifecycle != LifecycleState.OPEN:
        raise CallConflict("Звонок можно запросить только в открытом диалоге")
    if CallSession.objects.filter(
        conversation=conversation,
        status__in=UNFINISHED_CALL_STATUSES,
    ).exists():
        raise CallConflict("В диалоге уже есть незавершённый звонок")
    if CallSession.objects.filter(
        initiated_by=initiator,
        status__in=UNFINISHED_CALL_STATUSES,
    ).exists():
        raise CallConflict("Сотрудник уже участвует в другом звонке")
    if (
        conversation.control_mode == ControlMode.HUMAN
        and conversation.assigned_operator_id
        and conversation.assigned_operator_id != initiator.id
    ):
        raise CallConflict("Диалог уже ведёт другой оператор")


@transaction.atomic
def create_call_request(*, conversation_id: int, initiator) -> CreatedCall:
    conversation = (
        Conversation.objects.select_for_update()
        .select_related("channel")
        .get(id=conversation_id)
    )
    ensure_conversation_call_access(user=initiator, conversation=conversation)
    identity = _conversation_identity(conversation)
    _check_call_creation_conflicts(conversation=conversation, initiator=initiator)

    if conversation.control_mode != ControlMode.HUMAN or conversation.assigned_operator_id != initiator.id:
        try:
            claim_locked_conversation(conversation=conversation, operator=initiator)
        except ClaimError as error:
            raise CallConflict(str(error)) from error

    invite_token, token_hash = issue_invite_token()
    try:
        with transaction.atomic():
            call = CallSession.objects.create(
                organization_id=conversation.organization_id,
                conversation=conversation,
                initiated_by=initiator,
                delivery_connection_id=conversation.connection_id,
            )
    except IntegrityError as error:
        raise CallConflict("Не удалось создать второй незавершённый звонок") from error

    CallInvite.objects.create(
        call_session=call,
        connection_identity=identity,
        token_hash=token_hash,
        expires_at=timezone.now() + timedelta(seconds=settings.HUB_CALL_INVITE_TTL_SECONDS),
    )
    CallParticipant.objects.bulk_create(
        [
            CallParticipant(call_session=call, side=ParticipantSide.STAFF, user=initiator),
            CallParticipant(
                call_session=call,
                side=ParticipantSide.CUSTOMER,
                connection_identity=identity,
            ),
        ]
    )
    staff_token = issue_call_access_token(
        call_session_id=call.id,
        side=ParticipantSide.STAFF,
        subject_id=str(initiator.id),
    )
    return CreatedCall(call_session=call, invite_token=invite_token, staff_access_token=staff_token)


@transaction.atomic
def resolve_invite(*, token: str) -> ResolvedInvite:
    message = "Недействительное или истёкшее приглашение"
    invite = (
        CallInvite.objects.select_for_update()
        .select_related("call_session", "connection_identity")
        .filter(token_hash=hash_invite_token(token))
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


def issue_staff_access_token(*, call_session: CallSession, user) -> str:
    ensure_call_access(user=user, call_session=call_session)
    participant_exists = call_session.participants.filter(side=ParticipantSide.STAFF, user=user).exists()
    if not participant_exists:
        raise CallConflict("Сотрудник не является участником звонка")
    if call_session.status in TERMINAL_CALL_STATUSES:
        raise CallConflict("Звонок уже завершён")
    return issue_call_access_token(
        call_session_id=call_session.id,
        side=ParticipantSide.STAFF,
        subject_id=str(user.id),
    )


def authorize_call_access_token(*, token: str) -> tuple[CallAccessClaims, CallSession]:
    claims = verify_call_access_token(token)
    try:
        call = CallSession.objects.select_related("conversation", "conversation__channel").get(
            id=claims.call_session_id
        )
    except CallSession.DoesNotExist:
        raise CallTokenError("Недействительный или истёкший call access token") from None
    if call.status in TERMINAL_CALL_STATUSES:
        raise CallTokenError("Звонок уже завершён")
    if claims.side == ParticipantSide.STAFF:
        valid = call.participants.filter(
            side=ParticipantSide.STAFF,
            user_id=claims.subject_id,
        ).exists()
    else:
        invite = CallInvite.objects.filter(id=claims.subject_id, call_session=call).first()
        valid = invite is not None and (
            invite.expires_at > timezone.now()
            or call.status in {CallStatus.ACCEPTED, CallStatus.CONNECTING, CallStatus.ACTIVE}
        )
    if not valid:
        raise CallTokenError("Недействительный или истёкший call access token")
    return claims, call
