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


def _history_item(conversation: Conversation) -> dict[str, object]:
    last = _last_message(conversation)
    return {
        "id": conversation.id,
        "channelName": conversation.channel.name,
        "provider": conversation.connection.provider if conversation.connection_id else None,
        "lifecycle": conversation.lifecycle,
        "createdAt": conversation.created_at.isoformat(),
        "lastActivityAt": conversation.last_activity_at.isoformat(),
        "preview": last.text.replace("\n", " ")[:80] if last else "",
    }


def conversation_payload(conversation: Conversation, *, with_messages: bool = False) -> dict[str, object]:
    last = None if with_messages else _last_message(conversation)
    channel = conversation.channel
    payload = {
        "id": conversation.id,
        "channel": {
            "code": channel.code,
            "name": channel.name,
            "product": {"code": channel.product.code, "name": channel.product.name} if channel.product_id else None,
        },
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
        history = (
            Conversation.objects.filter(contact_id=conversation.contact_id)
            .exclude(id=conversation.id)
            .select_related("channel", "connection")
            .order_by("-last_activity_at")[:10]
        )
        payload["history"] = [_history_item(c) for c in history]
    else:
        payload["lastMessage"] = message_payload(last) if last else None
        payload["pendingCount"] = _pending_count(conversation)
    return payload
