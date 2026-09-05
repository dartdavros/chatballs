"""Доменные операции WebSocket-signaling (SPEC-HUB-0013 §9).

Вызываются consumer'ом через database_sync_to_async и возвращают готовые
payload-словари: ORM не утекает в async-контекст. Source of truth lifecycle —
PostgreSQL; Redis (channel layer) — только fan-out и presence.
"""

from django.utils import timezone

from chatballs.calls.errors import CallInvalidTransition
from chatballs.calls.lifecycle import finish_call, transition_call
from chatballs.calls.models import (
    CallParticipant,
    CallSession,
    CallStatus,
    ParticipantConnectionState,
    TERMINAL_CALL_STATUSES,
)
from chatballs.calls.serializers import public_call_state_payload
from chatballs.calls.services import record_call_metric
from chatballs.tenancy.context import TenantContext

def _call(context: TenantContext, call_id) -> CallSession:
    return CallSession.objects.select_related("initiated_by").get(
        id=call_id, organization=context.organization
    )


def call_state(context: TenantContext, call_id) -> dict:
    return public_call_state_payload(_call(context, call_id))


def call_status(context: TenantContext, call_id) -> str:
    return CallSession.objects.values_list("status", flat=True).get(
        id=call_id, organization=context.organization
    )


def _set_participant(
    context: TenantContext, call_id, side: str, *, state: str, joined: bool | None = None
) -> None:
    updates: dict = {"last_connection_state": state}
    if joined is True:
        updates["joined_at"] = timezone.now()
        updates["left_at"] = None
    if joined is False:
        updates["left_at"] = timezone.now()
    if state == ParticipantConnectionState.CONNECTED:
        # Восстановление после reconnect: сбрасываем таймер grace period.
        updates["left_at"] = None
    CallParticipant.objects.filter(
        call_session_id=call_id,
        call_session__organization=context.organization,
        side=side,
    ).update(**updates)


def signaling_join(context: TenantContext, call_id, side: str) -> dict:
    """Участник открыл signaling-соединение: presence + состояние звонка."""
    call = _call(context, call_id)
    if call.status not in TERMINAL_CALL_STATUSES:
        participant = CallParticipant.objects.filter(call_session_id=call_id, side=side).first()
        if participant is not None:
            participant.last_connection_state = ParticipantConnectionState.CONNECTING
            if participant.joined_at is None:
                participant.joined_at = timezone.now()
            participant.left_at = None
            participant.save(update_fields=["last_connection_state", "joined_at", "left_at"])
    return public_call_state_payload(call)


def signaling_leave(context: TenantContext, call_id, side: str) -> dict | None:
    """Разрыв WebSocket: participant DISCONNECTED, grace-таймер запускается.

    Возвращает None для завершённого звонка — уведомлять уже некого.
    """
    call = _call(context, call_id)
    if call.status in TERMINAL_CALL_STATUSES:
        return None
    _set_participant(
        context,
        call_id,
        side,
        state=ParticipantConnectionState.DISCONNECTED,
        joined=False,
    )
    return public_call_state_payload(call)


def start_negotiation(context: TenantContext, call_id) -> dict | None:
    """Первый SDP offer: ACCEPTED → CONNECTING. Возвращает payload при переходе."""
    if call_status(context, call_id) != CallStatus.ACCEPTED:
        return None
    try:
        call = transition_call(call_session_id=call_id, target_status=CallStatus.CONNECTING)
    except CallInvalidTransition:
        return None
    return public_call_state_payload(call)


def report_connection(
    context: TenantContext, call_id, side: str, connected: bool
) -> tuple[dict | None, bool]:
    """Участник сообщил состояние WebRTC-соединения.

    ACTIVE устанавливается только когда обе стороны подтвердили соединение
    (SPEC §5). Возвращает (payload при смене статуса звонка, became_active).
    """
    _set_participant(
        context,
        call_id,
        side,
        state=ParticipantConnectionState.CONNECTED if connected else ParticipantConnectionState.RECONNECTING,
        joined=False if not connected else None,
    )
    if not connected:
        return None, False
    status = call_status(context, call_id)
    if status not in {CallStatus.ACCEPTED, CallStatus.CONNECTING}:
        return None, False
    both_connected = (
        CallParticipant.objects.filter(
            call_session_id=call_id,
            call_session__organization=context.organization,
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


def record_metric(context: TenantContext, call_id, side: str, content: dict) -> None:
    """Метрики соединения от участника: только категория маршрута и RTT.

    Ничего не ретранслируется собеседнику и не логируется — payload не содержит
    медиаконтента, но и типы кандидатов наружу не пересылаются.
    """
    _call(context, call_id)
    record_call_metric(
        context=context,
        call_session_id=call_id,
        side=side,
        local_candidate_type=content.get("localCandidateType"),
        remote_candidate_type=content.get("remoteCandidateType"),
        round_trip_ms=content.get("roundTripMs"),
    )


def end_from_signaling(context: TenantContext, call_id, side: str) -> dict:
    """Завершение звонка стороной: идемпотентно, целевой статус — по фазе."""
    _call(context, call_id)
    call = finish_call(call_session_id=call_id, side=side)
    return public_call_state_payload(call)
