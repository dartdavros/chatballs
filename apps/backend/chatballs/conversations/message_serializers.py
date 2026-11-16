"""Employee message projection; delivery truth is independent of stored content."""

from chatballs.conversations.message_presentation import presentation_payload
from chatballs.conversations.models import Message, SystemEvent
from chatballs.conversations.site_fields import field_display
from chatballs.conversations.tool_call_events import tool_call_payload, tool_call_text
from chatballs.i18n import t
from chatballs.identity.avatars import user_avatar_url_in


def _system_text(message: Message) -> str:
    params = message.system_params or {}
    if message.system_event == SystemEvent.TOOL_CALLED:
        return tool_call_text(params)
    # Вид звонка приходит кодом (AUDIO/VIDEO): слово для него — тоже в каталоге.
    if params.get("kind"):
        params = {**params, "kind": t(f"calls.kind_{str(params['kind']).lower()}")}
    if message.system_event == SystemEvent.SITE_FIELDS_UPDATED:
        definition = {"type": params["fieldType"]}
        params = {**params, **{key: field_display(definition, params.get(key)) for key in ("old", "new")}}
    rendered = t(f"conversations.system.{message.system_event}", **params)
    # Ключа нет в каталоге — t вернул сам ключ; тогда честнее показать то, что
    # записано, чем служебный код.
    return message.text if rendered.startswith("conversations.system.") else rendered


def message_payload(message: Message) -> dict[str, object]:
    payload = {
        "id": message.id,
        "author": message.author_type,
        "authorUserId": message.author_user_id,
        # Подпись исходящего сообщения сотрудника (дизайн-базлайн v2, 4a).
        "authorName": (message.author_user.full_name or message.author_user.email) if message.author_user_id and message.author_user else "",
        "authorAvatarUrl": user_avatar_url_in(message.author_user, message.organization_id) if message.author_user_id and message.author_user else None,
        "kind": message.kind,
        # Системное событие собирается по коду на языке запроса: историю
        # диалога читают оба — и русскоязычный оператор, и англоязычный, — а
        # записана она один раз. Код без перевода и записи, сделанные до его
        # появления, приходят сохранённым текстом.
        "text": _system_text(message) if message.system_event else message.text,
        # Код нужен интерфейсу ещё и для тона строки: передача — предупреждение,
        # взятие — акцент. Раньше тон угадывался регуляркой по русским словам.
        "systemEvent": message.system_event,
        "contentHtml": message.content_html,
        **presentation_payload(message),
        "createdAt": message.created_at.isoformat(),
    }
    if message.kind == "voice":
        payload["audioUrl"] = (
            f"/api/v1/conversations/messages/{message.id}/audio/" if message.audio else None
        )
        payload["durationSeconds"] = message.duration_seconds
        payload["transcript"] = message.transcript
        payload["transcriptStatus"] = message.transcript_status
    if message.kind == "file":
        payload["attachmentUrl"] = (
            f"/api/v1/conversations/messages/{message.id}/attachment/" if message.attachment else None
        )
        payload["attachmentName"] = message.attachment_name
        payload["attachmentContentType"] = message.attachment_content_type
        payload["attachmentSize"] = message.attachment_size
    if message.system_event == SystemEvent.TOOL_CALLED:
        payload["toolCall"] = tool_call_payload(message.system_params or {})
    if message.system_event == SystemEvent.ASSIGNED_TO and (message.system_params or {}).get("transferId"):
        # Only a reference: reason/comment remain in the protected journal.
        payload["transferId"] = message.system_params["transferId"]
    from chatballs.ai.external_agents.ui_projection import message_status

    payload.update(message_status(message))
    letter = getattr(message, "email_transport", None)
    if letter:
        payload["transport"] = {"provider": "EMAIL", "connectionId": letter.connection_id,
                                "threadId": letter.thread_id, "direction": letter.direction,
                                "senderAddress": letter.sender_address or None,
                                "recipientAddress": letter.recipient_address or None,
                                "subject": letter.subject or None, "mailboxName": letter.mailbox_name or None}
    return payload
