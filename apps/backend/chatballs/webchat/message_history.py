"""Публичная история виджета: сообщения, состояние и приглашение на звонок."""

from chatballs.conversations.ai_turn import conversation_is_thinking
from chatballs.conversations.message_presentation import presentation_payload
from chatballs.conversations.models import (
    ControlMode,
    Conversation,
    LifecycleState,
    MessageKind,
    SystemEvent,
)
from chatballs.conversations.participant_notifications import customer_message_text
from chatballs.ratings.web_delivery import session_requests
from chatballs.webchat.author_avatars import author_payload, with_operator_authors
from chatballs.webchat.message_selectors import session_messages
from chatballs.webchat.models import WebSession

_STATE = {ControlMode.AI: "ai", ControlMode.HUMAN: "operator", ControlMode.PAUSED: "waiting"}
_ROLE = {"CONTACT": "client", "AI": "ai", "OPERATOR": "operator", "SYSTEM": "system"}


def _call_payload(session: WebSession) -> dict | None:
    # Приглашение на звонок для активной session (SPEC-CHATBALLS-0013 §7.1):
    # виджет получает его этим же поллингом, без отдельного realtime-канала.
    from chatballs.calls.serializers import public_invite_payload
    from chatballs.calls.services import webchat_active_call

    call = webchat_active_call(session.identity)
    if call is None:
        return None
    return public_invite_payload(call, call.invite.expires_at)


def _thread_is_gone(session: WebSession, since: int) -> bool:
    """Переписка, которую показывает виджет, перестала существовать.

    Диалог могли удалить в рабочем месте — вместе со всеми сообщениями. Тогда
    сообщения, до которого досчитал виджет, больше нет, и показывать клиенту
    переписку, которой не существует, нельзя. Закрытый диалог под это правило
    не подпадает: его сообщения на месте.
    """
    return since > 0 and not session_messages(session).filter(id=since).exists()


def messages_payload(session: WebSession, since: int) -> dict:
    from chatballs.webchat.proactive_status import status as site_status
    site_event = site_status(session)
    conversation = (
        Conversation.objects.filter(
            channel=session.connection.channel, connection=session.connection,
            contact=session.identity.contact, lifecycle=LifecycleState.OPEN
        )
        .order_by("-last_activity_at")
        .first()
    )
    reset = _thread_is_gone(session, since)
    from chatballs.speech.synthesis import public_synthesis

    playback = public_synthesis(session.connection)
    from chatballs.webchat.consent import has_current_consent

    consent_current = has_current_consent(session)
    if not consent_current:
        playback = {"playbackAvailable": False, "ttsRevision": ""}
    playback["consentCurrent"] = consent_current
    if reset:
        # Лента виджета начинается заново: то, что осталось, отдаётся целиком.
        since = 0
    if conversation is None:
        return {
            "playback": playback,
            "state": "ai" if _autonomous_session(session) else "waiting",
            "autonomous": _autonomous_session(session),
            "lifecycle": LifecycleState.OPEN,
            "messages": [],
            "call": None,
            "reset": reset,
            "thinking": site_event in ("pending", "running"),
            "siteEvent": site_event,
            "ratingRequests": session_requests(session),
        }
    # Изменения сайта и вызовы инструментов адресованы оператору: клиенту не
    # нужна пустая системная строка.
    items = with_operator_authors(session_messages(session), session).filter(
        conversation_id=conversation.pk, id__gt=since,
    ).order_by("created_at", "id")
    return {
        "playback": playback,
        "reset": reset,
        "autonomous": _autonomous_session(session),
        "state": _STATE.get(conversation.control_mode, "ai"),
        "lifecycle": conversation.lifecycle,
        # Ответ уже считается: виджет показывает клиенту, что агент печатает.
        "thinking": conversation_is_thinking(conversation.id) or site_event in ("pending", "running"),
        "siteEvent": site_event,
        "messages": [
            {
                "id": m.id,
                "author": _ROLE.get(m.author_type, "ai"),
                **author_payload(m),
                "kind": m.kind,
                "systemEvent": "specialist_joined" if m.system_event == SystemEvent.SPECIALIST_JOINED else "",
                "text": customer_message_text(m),
                **presentation_payload(m, public=True),
                "createdAt": m.created_at.isoformat(),
                "durationSeconds": m.duration_seconds,
                "hasAudio": bool(m.audio),
                **(
                    {
                        "attachment": {
                            "name": m.attachment_name,
                            "contentType": m.attachment_content_type,
                            "size": m.attachment_size,
                            "available": bool(m.attachment),
                        }
                    }
                    if m.kind == MessageKind.FILE
                    else {}
                ),
            }
            for m in items
        ],
        "call": _call_payload(session),
        "ratingRequests": session_requests(session),
    }


def _autonomous_session(session):
    from chatballs.webchat.configuration import _autonomous

    return _autonomous(session.connection)
