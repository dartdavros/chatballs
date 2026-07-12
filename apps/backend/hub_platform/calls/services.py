from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from hub_platform.calls.errors import CallConflict, CallInvalidTransition, CallTokenError
from hub_platform.calls.lifecycle import transition_call
from hub_platform.calls.models import (
    CallConnectionType,
    CallEndedBy,
    CallInvite,
    CallMetric,
    CallParticipant,
    CallSession,
    CallStatus,
    InviteDeliveryStatus,
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
    Message,
    MessageAuthor,
)
from hub_platform.conversations.services import ClaimError, claim_locked_conversation
from hub_platform.events.services import DomainEvent, enqueue_event
from hub_platform.integrations.models import IntegrationProvider

# Outbox-событие доставки приглашения в TG/MAX (обработчик — calls.event_handlers).
CALL_INVITE_SEND = "calls.invite_send"


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
    initiator_label = getattr(initiator, "full_name", "") or initiator.email
    Message.objects.create(
        conversation=conversation,
        author_type=MessageAuthor.SYSTEM,
        text=f"Оператор {initiator_label} запросил онлайн-звонок",
    )
    if conversation.connection.provider == IntegrationProvider.WEB:
        # Web Chat: приглашение забирает виджет поллингом, внешней отправки нет.
        call.invite.delivery_status = InviteDeliveryStatus.SENT
        call.invite.save(update_fields=["delivery_status"])
        call = transition_call(call_session_id=call.id, target_status=CallStatus.RINGING)
    else:
        # TG/MAX: кнопка со ссылкой /calls/<token> уходит через outbox с ретраями.
        enqueue_event(
            DomainEvent(
                aggregate_type="call_session",
                aggregate_id=str(call.id),
                event_type=CALL_INVITE_SEND,
                payload={"callSessionId": str(call.id)},
            )
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


def authorize_call_access_token(*, token: str, allow_terminal: bool = False) -> tuple[CallAccessClaims, CallSession]:
    claims = verify_call_access_token(token)
    try:
        call = CallSession.objects.select_related(
            "conversation", "conversation__channel", "initiated_by"
        ).get(id=claims.call_session_id)
    except CallSession.DoesNotExist:
        raise CallTokenError("Недействительный или истёкший call access token") from None
    if call.status in TERMINAL_CALL_STATUSES and not allow_terminal:
        raise CallTokenError("Звонок уже завершён")
    if claims.side == ParticipantSide.STAFF:
        valid = call.participants.filter(
            side=ParticipantSide.STAFF,
            user_id=claims.subject_id,
        ).exists()
    else:
        # После принятия/завершения истечение invite не отзывает доступ к
        # состоянию: TTL самого access token остаётся единственным пределом.
        invite = CallInvite.objects.filter(id=claims.subject_id, call_session=call).first()
        valid = invite is not None and (
            invite.expires_at > timezone.now()
            or call.status not in {CallStatus.REQUESTED, CallStatus.RINGING}
        )
    if not valid:
        raise CallTokenError("Недействительный или истёкший call access token")
    return claims, call


def cancel_call(*, call_session: CallSession, user) -> CallSession:
    ensure_call_access(user=user, call_session=call_session)
    if not call_session.participants.filter(side=ParticipantSide.STAFF, user=user).exists():
        raise CallConflict("Сотрудник не является участником звонка")
    try:
        # Повторная отмена идемпотентна: transition_call вернёт звонок без изменений.
        return transition_call(
            call_session_id=call_session.id,
            target_status=CallStatus.CANCELLED,
            ended_by=CallEndedBy.STAFF,
        )
    except CallInvalidTransition as error:
        raise CallConflict("Звонок уже нельзя отменить") from error


def _customer_call(*, token: str, allow_terminal: bool = False) -> CallSession:
    claims, call = authorize_call_access_token(token=token, allow_terminal=allow_terminal)
    if claims.side != ParticipantSide.CUSTOMER:
        raise CallTokenError("Недействительный или истёкший call access token")
    return call


def accept_call_by_access_token(*, token: str) -> CallSession:
    call = _customer_call(token=token)
    try:
        if call.status == CallStatus.REQUESTED:
            call = transition_call(call_session_id=call.id, target_status=CallStatus.RINGING)
        return transition_call(call_session_id=call.id, target_status=CallStatus.ACCEPTED)
    except CallInvalidTransition as error:
        raise CallConflict("Приглашение уже нельзя принять") from error


def decline_call_by_access_token(*, token: str) -> CallSession:
    call = _customer_call(token=token, allow_terminal=True)
    if call.status == CallStatus.DECLINED:
        return call
    try:
        return transition_call(
            call_session_id=call.id,
            target_status=CallStatus.DECLINED,
            ended_by=CallEndedBy.CUSTOMER,
        )
    except CallInvalidTransition as error:
        raise CallConflict("Приглашение уже нельзя отклонить") from error


def call_state_by_access_token(*, token: str) -> CallSession:
    _claims, call = authorize_call_access_token(token=token, allow_terminal=True)
    return call


# ICE candidate типы (RFC 8445), допустимые в метриках. Храним только категорию,
# без адреса/порта/foundation самого кандидата.
_ALLOWED_CANDIDATE_TYPES = {"host", "srflx", "prflx", "relay"}
_MAX_ROUND_TRIP_MS = 60_000


def _sanitize_candidate_type(value) -> str:
    text = str(value or "").lower()
    return text if text in _ALLOWED_CANDIDATE_TYPES else ""


def _connection_type(local: str, remote: str) -> str:
    if "relay" in (local, remote):
        return CallConnectionType.RELAY
    if local or remote:
        return CallConnectionType.DIRECT
    return CallConnectionType.UNKNOWN


def record_call_metric(
    *,
    call_session_id,
    side: str,
    local_candidate_type=None,
    remote_candidate_type=None,
    round_trip_ms=None,
) -> None:
    """Сохранить технические метрики соединения участника (без медиаконтента).

    Идемпотентно по (call_session, side): при reconnect/ICE-restart метрика
    обновляется актуальным типом маршрута. Никакие SDP/ICE payload не пишутся —
    только производная категория кандидата и RTT.
    """
    if side not in ParticipantSide.values:
        return
    if not CallSession.objects.filter(id=call_session_id).exists():
        return
    local = _sanitize_candidate_type(local_candidate_type)
    remote = _sanitize_candidate_type(remote_candidate_type)
    rtt: int | None = None
    if isinstance(round_trip_ms, (int, float)) and not isinstance(round_trip_ms, bool):
        rtt = max(0, min(_MAX_ROUND_TRIP_MS, int(round_trip_ms)))
    CallMetric.objects.update_or_create(
        call_session_id=call_session_id,
        side=side,
        defaults={
            "connection_type": _connection_type(local, remote),
            "local_candidate_type": local,
            "remote_candidate_type": remote,
            "round_trip_ms": rtt,
        },
    )


def active_call_for_conversation(conversation: Conversation) -> CallSession | None:
    return (
        CallSession.objects.filter(
            conversation=conversation,
            status__in=UNFINISHED_CALL_STATUSES,
        )
        .select_related("initiated_by")
        .prefetch_related("participants")
        .first()
    )


# --- Web Chat: приглашение доставляется поллингом виджета по session identity ---


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
        raise CallTokenError("Активное приглашение не найдено")
    invite = CallInvite.objects.select_for_update().get(call_session=call)
    if invite.expires_at <= timezone.now():
        raise CallTokenError("Активное приглашение не найдено")
    if invite.opened_at is None:
        invite.opened_at = timezone.now()
        invite.save(update_fields=["opened_at"])
    access_token = issue_call_access_token(
        call_session_id=call.id,
        side=ParticipantSide.CUSTOMER,
        subject_id=str(invite.id),
    )
    return ResolvedInvite(invite=invite, customer_access_token=access_token)


def decline_call_for_identity(*, identity: ConnectionIdentity) -> CallSession:
    call = webchat_active_call(identity)
    if call is None:
        raise CallTokenError("Активное приглашение не найдено")
    try:
        return transition_call(
            call_session_id=call.id,
            target_status=CallStatus.DECLINED,
            ended_by=CallEndedBy.CUSTOMER,
        )
    except CallInvalidTransition as error:
        raise CallConflict("Приглашение уже нельзя отклонить") from error
