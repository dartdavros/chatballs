"""Серверные таймауты звонков (SPEC-HUB-0013 §5): истечение приглашения и
зависшее соединение обрабатываются воркером, а не браузером клиента."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from hub_platform.calls.errors import CallInvalidTransition
from hub_platform.calls.lifecycle import transition_call
from hub_platform.calls.models import CallEndedBy, CallSession, CallStatus


def expire_stale_calls() -> int:
    now = timezone.now()
    finished = 0

    # Приглашение истекло: доставленное — MISSED (клиент не ответил),
    # недоставленное — EXPIRED.
    pending = CallSession.objects.filter(
        status__in=[CallStatus.REQUESTED, CallStatus.RINGING],
        invite__expires_at__lte=now,
    ).values_list("id", "status")
    for call_id, status in pending:
        target = CallStatus.MISSED if status == CallStatus.RINGING else CallStatus.EXPIRED
        try:
            transition_call(call_session_id=call_id, target_status=target, ended_by=CallEndedBy.TIMEOUT)
            finished += 1
        except CallInvalidTransition:
            continue  # состояние сменилось между выборкой и переходом

    # Принятый звонок без установленного соединения дольше grace period — FAILED.
    connect_deadline = now - timedelta(seconds=settings.HUB_CALL_CONNECT_GRACE_SECONDS)
    stuck = CallSession.objects.filter(
        status__in=[CallStatus.ACCEPTED, CallStatus.CONNECTING],
        accepted_at__lte=connect_deadline,
    ).values_list("id", flat=True)
    for call_id in stuck:
        try:
            transition_call(
                call_session_id=call_id,
                target_status=CallStatus.FAILED,
                ended_by=CallEndedBy.TIMEOUT,
                failure_code="CONNECT_TIMEOUT",
            )
            finished += 1
        except CallInvalidTransition:
            continue
    return finished
