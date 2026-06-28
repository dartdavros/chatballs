from hub_platform.conversations.models import Conversation, Message, MessageAuthor


def message_payload(message: Message) -> dict[str, object]:
    return {
        "id": message.id,
        "author": message.author_type,
        "authorUserId": message.author_user_id,
        "text": message.text,
        "createdAt": message.created_at.isoformat(),
    }


def _last_message(conversation: Conversation) -> Message | None:
    return conversation.messages.order_by("-created_at").first()


def _pending_count(conversation: Conversation) -> int:
    # Сообщения клиента, пришедшие после последнего ответа AI/оператора (ожидают ответа).
    count = 0
    for message in conversation.messages.order_by("-created_at")[:50]:
        if message.author_type == MessageAuthor.CONTACT:
            count += 1
        else:
            break
    return count


def conversation_payload(conversation: Conversation, *, with_messages: bool = False) -> dict[str, object]:
    last = None if with_messages else _last_message(conversation)
    payload = {
        "id": conversation.id,
        "channel": {"code": conversation.channel.code, "name": conversation.channel.name},
        "connection": (
            {"id": conversation.connection_id, "provider": conversation.connection.provider, "name": conversation.connection.name}
            if conversation.connection_id
            else None
        ),
        "contact": {"id": conversation.contact_id, "name": conversation.contact.name},
        "lifecycle": conversation.lifecycle,
        "controlMode": conversation.control_mode,
        "expectedResponder": conversation.expected_responder,
        "assignedOperatorId": conversation.assigned_operator_id,
        "lastActivityAt": conversation.last_activity_at.isoformat(),
        "createdAt": conversation.created_at.isoformat(),
    }
    if with_messages:
        payload["messages"] = [message_payload(m) for m in conversation.messages.order_by("created_at")]
    else:
        payload["lastMessage"] = message_payload(last) if last else None
        payload["pendingCount"] = _pending_count(conversation)
    return payload
