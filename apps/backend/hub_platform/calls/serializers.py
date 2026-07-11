from hub_platform.calls.models import CallSession


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
    return {
        "id": str(call.id),
        "conversationId": call.conversation_id,
        "status": call.status,
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
    }


def public_invite_payload(call: CallSession, expires_at) -> dict:
    return {
        "callId": str(call.id),
        "status": call.status,
        "expiresAt": expires_at.isoformat(),
        "staffName": _staff_label(call),
        "capabilities": {"audio": True, "video": True},
    }


def _staff_label(call: CallSession) -> str:
    return getattr(call.initiated_by, "full_name", "") or "Оператор"


def public_call_state_payload(call: CallSession) -> dict:
    # Клиентская страница звонка: только lifecycle, без внутренних ID и данных диалога.
    return {
        "callId": str(call.id),
        "status": call.status,
        "staffName": _staff_label(call),
        "endedBy": call.ended_by or None,
        "durationSeconds": call.duration_seconds,
    }
