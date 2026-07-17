"""Серверные таймауты звонков (SPEC-HUB-0013 §5): истечение приглашения и
зависшее соединение обрабатываются воркером, а не браузером клиента."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from hub_platform.calls.errors import CallInvalidTransition
from hub_platform.calls.lifecycle import transition_call
from hub_platform.calls.models import CallEndedBy, CallSession, CallStatus


def expire_stale_calls(context) -> int:
    now = timezone.now()
    finished = 0

    # Приглашение истекло: доставленное — MISSED (клиент не ответил),
    # недоставленное — EXPIRED.
    pending = CallSession.objects.filter(
        organization=context.organization,
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
    connect_deadline = now - timedelta(seconds=settings.CUS_CALL_CONNECT_GRACE_SECONDS)
    stuck = CallSession.objects.filter(
        organization=context.organization,
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

    # Активный звонок с участником, не восстановившимся после обрыва (SPEC §5:
    # временный обрыв → reconnecting, после grace period — FAILED).
    reconnect_deadline = now - timedelta(seconds=settings.CUS_CALL_RECONNECT_GRACE_SECONDS)
    dropped = (
        CallSession.objects.filter(
            organization=context.organization,
            status=CallStatus.ACTIVE,
            participants__left_at__lte=reconnect_deadline,
        )
        .distinct()
        .values_list("id", flat=True)
    )
    for call_id in dropped:
        try:
            transition_call(
                call_session_id=call_id,
                target_status=CallStatus.FAILED,
                ended_by=CallEndedBy.TIMEOUT,
                failure_code="PEER_DISCONNECTED",
            )
            finished += 1
        except CallInvalidTransition:
            continue
    return finished
