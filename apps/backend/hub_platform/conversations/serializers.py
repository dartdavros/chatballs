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


def _support_identity_snapshot(
    conversation: Conversation, *, detailed: bool = False
) -> dict[str, object] | None:
    snapshot = conversation.support_identity_snapshot
    if snapshot is None:
        return None
    # Краткая карточка для списка диалогов; в detail-режиме — operator_context_json
    # + account_key для правой панели оператора (ADR-HUB-0022 §8.3: рендер по контракту).
    payload: dict[str, object] = {
        "id": snapshot.id,
        "subjectKey": snapshot.subject_key,
        "displayName": snapshot.display_name,
        "displayEmail": snapshot.display_email,
        "contractCode": snapshot.contract_code,
    }
    if detailed:
        payload["accountKey"] = snapshot.account_key
        payload["operatorContextJson"] = snapshot.operator_context_json
    return payload


def _conversation_history(conversation: Conversation) -> list[Conversation]:
    # История по тому же источнику identity: для sales — по contact, для
    # support — по snapshot (ADR-HUB-0002: цепочка прошлых обращений).
    if conversation.support_identity_snapshot_id:
        qs = Conversation.objects.filter(
            support_identity_snapshot_id=conversation.support_identity_snapshot_id
        )
    else:
        qs = Conversation.objects.filter(contact_id=conversation.contact_id)
    return list(
        qs.exclude(id=conversation.id)
        .select_related("channel", "connection")
        .order_by("-last_activity_at")[:10]
    )


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
        # Источник identity: sales Contact ИЛИ verified SupportIdentitySnapshot.
        # Для support-диалогов contact=None, клиент представлен snapshot'ом.
        "contact": (
            {"id": conversation.contact_id, "name": conversation.contact.name}
            if conversation.contact_id
            else None
        ),
        "supportIdentitySnapshot": _support_identity_snapshot(conversation, detailed=with_messages),
        "lifecycle": conversation.lifecycle,
        "controlMode": conversation.control_mode,
        "expectedResponder": conversation.expected_responder,
        "assignedOperatorId": conversation.assigned_operator_id,
        "lastActivityAt": conversation.last_activity_at.isoformat(),
        "createdAt": conversation.created_at.isoformat(),
    }
    if with_messages:
        payload["messages"] = [message_payload(m) for m in conversation.messages.order_by("created_at")]
        history = _conversation_history(conversation)
        payload["history"] = [_history_item(c) for c in history]
    else:
        payload["lastMessage"] = message_payload(last) if last else None
        payload["pendingCount"] = _pending_count(conversation)
    return payload
