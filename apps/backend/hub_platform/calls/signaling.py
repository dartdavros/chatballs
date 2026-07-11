"""Доменные операции WebSocket-signaling (SPEC-HUB-0013 §9).

Вызываются consumer'ом через database_sync_to_async и возвращают готовые
payload-словари: ORM не утекает в async-контекст. Source of truth lifecycle —
PostgreSQL; Redis (channel layer) — только fan-out и presence.
"""

from django.utils import timezone

from hub_platform.calls.errors import CallInvalidTransition
from hub_platform.calls.lifecycle import transition_call
from hub_platform.calls.models import (
    CallEndedBy,
    CallParticipant,
    CallSession,
    CallStatus,
    ParticipantConnectionState,
    ParticipantSide,
    TERMINAL_CALL_STATUSES,
)
from hub_platform.calls.serializers import public_call_state_payload

SIDE_TO_ENDED_BY = {
    ParticipantSide.STAFF: CallEndedBy.STAFF,
    ParticipantSide.CUSTOMER: CallEndedBy.CUSTOMER,
}


def _call(call_id) -> CallSession:
    return CallSession.objects.select_related("initiated_by").get(id=call_id)


def call_state(call_id) -> dict:
    return public_call_state_payload(_call(call_id))


def call_status(call_id) -> str:
    return CallSession.objects.values_list("status", flat=True).get(id=call_id)


def _set_participant(call_id, side: str, *, state: str, joined: bool | None = None) -> None:
    updates: dict = {"last_connection_state": state}
    if joined is True:
        updates["joined_at"] = timezone.now()
        updates["left_at"] = None
    if joined is False:
        updates["left_at"] = timezone.now()
    if state == ParticipantConnectionState.CONNECTED:
        # Восстановление после reconnect: сбрасываем таймер grace period.
        updates["left_at"] = None
    CallParticipant.objects.filter(call_session_id=call_id, side=side).update(**updates)


def signaling_join(call_id, side: str) -> dict:
    """Участник открыл signaling-соединение: presence + состояние звонка."""
    call = _call(call_id)
    if call.status not in TERMINAL_CALL_STATUSES:
        participant = CallParticipant.objects.filter(call_session_id=call_id, side=side).first()
        if participant is not None:
            participant.last_connection_state = ParticipantConnectionState.CONNECTING
            if participant.joined_at is None:
                participant.joined_at = timezone.now()
            participant.left_at = None
            participant.save(update_fields=["last_connection_state", "joined_at", "left_at"])
    return public_call_state_payload(call)


def signaling_leave(call_id, side: str) -> dict | None:
    """Разрыв WebSocket: participant DISCONNECTED, grace-таймер запускается.

    Возвращает None для завершённого звонка — уведомлять уже некого.
    """
    call = _call(call_id)
    if call.status in TERMINAL_CALL_STATUSES:
        return None
    _set_participant(call_id, side, state=ParticipantConnectionState.DISCONNECTED, joined=False)
    return public_call_state_payload(call)


def start_negotiation(call_id) -> dict | None:
    """Первый SDP offer: ACCEPTED → CONNECTING. Возвращает payload при переходе."""
    if call_status(call_id) != CallStatus.ACCEPTED:
        return None
    try:
        call = transition_call(call_session_id=call_id, target_status=CallStatus.CONNECTING)
    except CallInvalidTransition:
        return None
    return public_call_state_payload(call)


def report_connection(call_id, side: str, connected: bool) -> tuple[dict | None, bool]:
    """Участник сообщил состояние WebRTC-соединения.

    ACTIVE устанавливается только когда обе стороны подтвердили соединение
    (SPEC §5). Возвращает (payload при смене статуса звонка, became_active).
    """
    _set_participant(
        call_id,
        side,
        state=ParticipantConnectionState.CONNECTED if connected else ParticipantConnectionState.RECONNECTING,
        joined=False if not connected else None,
    )
    if not connected:
        return None, False
    status = call_status(call_id)
    if status not in {CallStatus.ACCEPTED, CallStatus.CONNECTING}:
        return None, False
    both_connected = (
        CallParticipant.objects.filter(
            call_session_id=call_id,
            last_connection_state=ParticipantConnectionState.CONNECTED,
        ).count()
        == 2
    )
    if not both_connected:
        return None, False
    try:
        if status == CallStatus.ACCEPTED:
            transition_call(call_session_id=call_id, target_status=CallStatus.CONNECTING)
        call = transition_call(call_session_id=call_id, target_status=CallStatus.ACTIVE)
    except CallInvalidTransition:
        return None, False
    return public_call_state_payload(call), True


def end_from_signaling(call_id, side: str) -> dict:
    """Завершение звонка стороной: идемпотентно, целевой статус — по фазе."""
    ended_by = SIDE_TO_ENDED_BY.get(side, CallEndedBy.SYSTEM)
    call = _call(call_id)
    if call.status in TERMINAL_CALL_STATUSES:
        return public_call_state_payload(call)
    try:
        if call.status == CallStatus.ACTIVE:
            call = transition_call(call_session_id=call_id, target_status=CallStatus.ENDED, ended_by=ended_by)
        elif call.status in {CallStatus.ACCEPTED, CallStatus.CONNECTING}:
            call = transition_call(
                call_session_id=call_id,
                target_status=CallStatus.FAILED,
                ended_by=ended_by,
                failure_code="ABORTED_BEFORE_CONNECT",
            )
        elif side == ParticipantSide.STAFF:
            call = transition_call(call_session_id=call_id, target_status=CallStatus.CANCELLED, ended_by=ended_by)
        else:
            call = transition_call(call_session_id=call_id, target_status=CallStatus.DECLINED, ended_by=ended_by)
    except CallInvalidTransition:
        call = _call(call_id)
    return public_call_state_payload(call)
