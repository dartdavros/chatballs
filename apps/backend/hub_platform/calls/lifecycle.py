import re

from django.db import transaction
from django.utils import timezone

from hub_platform.calls.errors import CallInvalidTransition
from hub_platform.calls.models import (
    CallEndedBy,
    CallSession,
    CallStatus,
    TERMINAL_CALL_STATUSES,
)

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
        raise CallInvalidTransition(f"Переход {call.status} -> {target_status} запрещён")
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
    return call
