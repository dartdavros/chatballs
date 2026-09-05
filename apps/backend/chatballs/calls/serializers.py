from django.conf import settings

from chatballs.calls.models import CallSession
from chatballs.calls.turn import turn_credentials


def _iso(value):
    return value.isoformat() if value else None


def call_payload(call: CallSession) -> dict:
    participants = [
        {
            "side": participant.side,
            "connectionState": participant.last_connection_state,
            "joinedAt": _iso(participant.joined_at),
            "leftAt": _iso(participant.left_at),
        }
        for participant in call.participants.all()
    ]
    metrics = [
        {
            "side": metric.side,
            "connectionType": metric.connection_type,
            "localCandidateType": metric.local_candidate_type or None,
            "remoteCandidateType": metric.remote_candidate_type or None,
            "roundTripMs": metric.round_trip_ms,
        }
        for metric in call.metrics.all()
    ]
    return {
        "id": str(call.id),
        "conversationId": call.conversation_id,
        "status": call.status,
        "kind": call.kind,
        "initiatedByUserId": call.initiated_by_id,
        "deliveryConnectionId": call.delivery_connection_id,
        "requestedAt": _iso(call.requested_at),
        "acceptedAt": _iso(call.accepted_at),
        "connectedAt": _iso(call.connected_at),
        "endedAt": _iso(call.ended_at),
        "endedBy": call.ended_by or None,
        "failureCode": call.failure_code or None,
        "durationSeconds": call.duration_seconds,
        "participants": participants,
        "metrics": metrics,
    }


def public_invite_payload(call: CallSession, expires_at) -> dict:
    return {
        "callId": str(call.id),
        "status": call.status,
        "kind": call.kind,
        "expiresAt": expires_at.isoformat(),
        "staffName": _staff_label(call),
    }


def _staff_label(call: CallSession) -> str:
    return getattr(call.initiated_by, "full_name", "") or "Оператор"


def ice_servers_payload() -> list[dict]:
    # ICE-конфигурация клиента (SPEC §10): direct-first через STUN, TURN как
    # fallback с краткоживущими credentials. Генерируется на каждый запрос токена,
    # поэтому клиент всегда получает не истёкшие TURN credentials.
    servers: list[dict] = []
    if settings.CHATBALLS_CALL_STUN_URLS:
        servers.append({"urls": list(settings.CHATBALLS_CALL_STUN_URLS)})
    if settings.CHATBALLS_CALL_TURN_URLS and settings.CHATBALLS_CALL_TURN_SECRET:
        username, credential = turn_credentials()
        servers.append(
            {
                "urls": list(settings.CHATBALLS_CALL_TURN_URLS),
                "username": username,
                "credential": credential,
            }
        )
    return servers


def public_call_state_payload(call: CallSession) -> dict:
    # Клиентская страница звонка: только lifecycle, без внутренних ID и данных диалога.
    return {
        "callId": str(call.id),
        "status": call.status,
        "kind": call.kind,
        "staffName": _staff_label(call),
        "endedBy": call.ended_by or None,
        "durationSeconds": call.duration_seconds,
    }
