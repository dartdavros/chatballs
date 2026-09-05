from __future__ import annotations

from chatballs.calls.models import (
    CallConnectionType,
    CallMetric,
    CallSession,
    ParticipantSide,
)
from chatballs.tenancy.context import TenantContext

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
    context: TenantContext,
    call_session_id,
    side: str,
    local_candidate_type=None,
    remote_candidate_type=None,
    round_trip_ms=None,
) -> None:
    """Persist derived connection metrics without SDP, ICE addresses or media."""

    if side not in ParticipantSide.values:
        return
    if not CallSession.objects.filter(
        id=call_session_id,
        organization=context.organization,
    ).exists():
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
            "organization": context.organization,
            "connection_type": _connection_type(local, remote),
            "local_candidate_type": local,
            "remote_candidate_type": remote,
            "round_trip_ms": rtt,
        },
    )
