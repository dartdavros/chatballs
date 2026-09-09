import re

from django.db import transaction
from django.utils import timezone

from chatballs.calls.errors import CallInvalidTransition
from chatballs.calls.models import (
    TERMINAL_CALL_STATUSES,
    CallEndedBy,
    CallSession,
    CallStatus,
    ParticipantSide,
)
from chatballs.conversations.models import Message, MessageAuthor, SystemEvent
from chatballs.i18n import t

ALLOWED_TRANSITIONS = {
    CallStatus.REQUESTED: {
        CallStatus.RINGING,
        CallStatus.DECLINED,
        CallStatus.CANCELLED,
        CallStatus.MISSED,
        CallStatus.EXPIRED,
    },
    CallStatus.RINGING: {
        CallStatus.ACCEPTED,
        CallStatus.DECLINED,
        CallStatus.CANCELLED,
        CallStatus.MISSED,
        CallStatus.EXPIRED,
    },
    CallStatus.ACCEPTED: {CallStatus.CONNECTING, CallStatus.FAILED},
    CallStatus.CONNECTING: {CallStatus.ACTIVE, CallStatus.FAILED},
    CallStatus.ACTIVE: {CallStatus.ENDED, CallStatus.FAILED},
}
FAILURE_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


def _format_duration(seconds: int) -> str:
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


# Код события и его параметры: интерфейс собирает фразу на языке читателя, а
# текст остаётся в базе запасным вариантом и читаемой записью.
_TIMELINE_EVENTS: dict[str, str] = {
    CallStatus.ACCEPTED: SystemEvent.CALL_ACCEPTED,
    CallStatus.DECLINED: SystemEvent.CALL_DECLINED,
    CallStatus.CANCELLED: SystemEvent.CALL_CANCELLED,
    CallStatus.MISSED: SystemEvent.CALL_MISSED,
    CallStatus.EXPIRED: SystemEvent.CALL_EXPIRED,
    CallStatus.ACTIVE: SystemEvent.CALL_STARTED,
    CallStatus.ENDED: SystemEvent.CALL_ENDED,
    CallStatus.FAILED: SystemEvent.CALL_FAILED,
}


def _timeline_event(call: CallSession, target_status: str) -> tuple[str, dict]:
    """Код события и параметры для строки таймлайна."""

    code = _TIMELINE_EVENTS.get(target_status, "")
    if code == SystemEvent.CALL_ENDED and call.duration_seconds is not None:
        return code, {"duration": _format_duration(call.duration_seconds)}
    return code, {}


def _timeline_text(call: CallSession, target_status: str) -> str | None:
    # Системные события звонка в timeline диалога (SPEC-CHATBALLS-0013 §13).
    # Вызывается только при фактической смене статуса — retry дублей не даёт.
    if target_status == CallStatus.ACCEPTED:
        return "Клиент принял приглашение на звонок"
    if target_status == CallStatus.DECLINED:
        return "Клиент отклонил приглашение на звонок"
    if target_status == CallStatus.CANCELLED:
        return "Сотрудник отменил приглашение на звонок"
    if target_status == CallStatus.MISSED:
        return "Звонок пропущен: клиент не ответил"
    if target_status == CallStatus.EXPIRED:
        return "Приглашение на звонок истекло"
    if target_status == CallStatus.ACTIVE:
        return "Звонок начался: соединение установлено"
    if target_status == CallStatus.ENDED:
        duration = call.duration_seconds
        if duration is not None:
            return f"Звонок завершён · {_format_duration(duration)}"
        return "Звонок завершён"
    if target_status == CallStatus.FAILED:
        return "Звонок завершился технической ошибкой"
    return None


@transaction.atomic
def transition_call(
    *,
    call_session_id,
    target_status: str,
    ended_by: str = CallEndedBy.SYSTEM,
    failure_code: str = "",
) -> CallSession:
    call = CallSession.objects.select_for_update().get(id=call_session_id)
    if target_status == call.status:
        return call
    if target_status not in ALLOWED_TRANSITIONS.get(call.status, set()):
        raise CallInvalidTransition(
            t("calls.transition_forbidden", current=call.status, target=target_status)
        )
    normalized_failure_code = failure_code.strip()
    if target_status == CallStatus.FAILED and not FAILURE_CODE_PATTERN.fullmatch(normalized_failure_code):
        raise CallInvalidTransition("Для FAILED требуется нормализованный failure_code")

    now = timezone.now()
    update_fields = ["status", "updated_at"]
    call.status = target_status
    if target_status == CallStatus.ACCEPTED:
        call.accepted_at = call.accepted_at or now
        update_fields.append("accepted_at")
        if hasattr(call, "invite") and call.invite.responded_at is None:
            call.invite.responded_at = now
            call.invite.save(update_fields=["responded_at"])
    if target_status == CallStatus.ACTIVE:
        call.connected_at = call.connected_at or now
        update_fields.append("connected_at")
    if target_status in TERMINAL_CALL_STATUSES:
        call.ended_at = call.ended_at or now
        call.ended_by = ended_by
        update_fields.extend(["ended_at", "ended_by"])
    if target_status == CallStatus.DECLINED and hasattr(call, "invite") and call.invite.responded_at is None:
        call.invite.responded_at = now
        call.invite.save(update_fields=["responded_at"])
    if target_status == CallStatus.FAILED:
        call.failure_code = normalized_failure_code
        update_fields.append("failure_code")
    call.save(update_fields=update_fields)
    timeline_text = _timeline_text(call, target_status)
    if timeline_text is not None:
        event, params = _timeline_event(call, target_status)
        Message.objects.create(
            conversation_id=call.conversation_id,
            author_type=MessageAuthor.SYSTEM,
            system_event=event,
            system_params=params,
            text=timeline_text,
        )
    return call


@transaction.atomic
def finish_call(*, call_session_id, side: str) -> CallSession:
    """Надёжно завершает звонок из любой незавершённой фазы.

    Используется и REST access endpoint'ом, и WebSocket signaling, чтобы закрытие
    вкладки/модального окна не оставляло ACCEPTED/CONNECTING звонок зависшим.
    """
    # Блокировка не позволяет конкурентному signaling-событию перевести звонок
    # между чтением статуса и завершающим переходом.
    call = CallSession.objects.select_for_update().get(id=call_session_id)
    if call.status in TERMINAL_CALL_STATUSES:
        return call
    ended_by = CallEndedBy.STAFF if side == ParticipantSide.STAFF else CallEndedBy.CUSTOMER
    if call.status == CallStatus.ACTIVE:
        target_status = CallStatus.ENDED
        failure_code = ""
    elif call.status in {CallStatus.ACCEPTED, CallStatus.CONNECTING}:
        target_status = CallStatus.FAILED
        failure_code = "ABORTED_BEFORE_CONNECT"
    elif side == ParticipantSide.STAFF:
        target_status = CallStatus.CANCELLED
        failure_code = ""
    else:
        target_status = CallStatus.DECLINED
        failure_code = ""
    return transition_call(
        call_session_id=call.id,
        target_status=target_status,
        ended_by=ended_by,
        failure_code=failure_code,
    )
