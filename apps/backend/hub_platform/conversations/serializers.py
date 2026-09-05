from hub_platform.conversations.models import ConnectionIdentity, Conversation, Message, MessageAuthor
from hub_platform.identity.avatars import user_avatar_url_in
from hub_platform.integrations.models import IntegrationProvider


def message_payload(message: Message) -> dict[str, object]:
    payload = {
        "id": message.id,
        "author": message.author_type,
        "authorUserId": message.author_user_id,
        # Подпись исходящего сообщения сотрудника (дизайн-базлайн v2, 4a).
        "authorName": (message.author_user.full_name or message.author_user.email) if message.author_user_id and message.author_user else "",
        "authorAvatarUrl": user_avatar_url_in(message.author_user, message.organization_id) if message.author_user_id and message.author_user else None,
        "kind": message.kind,
        "text": message.text,
        "contentHtml": message.content_html,
        "createdAt": message.created_at.isoformat(),
    }
    if message.kind == "voice":
        payload["audioUrl"] = (
            f"/api/v1/conversations/messages/{message.id}/audio/" if message.audio else None
        )
        payload["durationSeconds"] = message.duration_seconds
        payload["transcript"] = message.transcript
        payload["transcriptStatus"] = message.transcript_status
    return payload


def _last_message(conversation: Conversation) -> Message | None:
    # Превью строки списка — последняя реплика клиента/AI/сотрудника; системные
    # события («AI передал диалог») в превью не показываются (дизайн-базлайн v2, B).
    return (
        conversation.messages.exclude(author_type=MessageAuthor.SYSTEM)
        .select_related("author_user")
        .order_by("-created_at", "-id")
        .first()
    )


def _pending_count(conversation: Conversation, last_read_id: int = 0) -> int:
    # Бейдж непрочитанных: хвост клиентских сообщений (после последнего ответа
    # AI/оператора), которые просматривающий ещё не открывал (id > отметки
    # прочтения). Открытие диалога двигает отметку — бейдж гаснет.
    count = 0
    for message in conversation.messages.order_by("-created_at")[:50]:
        if message.author_type != MessageAuthor.CONTACT:
            break
        if message.id > last_read_id:
            count += 1
    return count


def _history_item(conversation: Conversation) -> dict[str, object]:
    last = _last_message(conversation)
    # Тема карточки истории (кадр F) — первая реплика клиента; кто вёл — ответственный или AI.
    first = (
        conversation.messages.filter(author_type=MessageAuthor.CONTACT)
        .order_by("created_at", "id")
        .values_list("text", flat=True)
        .first()
    )
    operator = conversation.assigned_operator
    return {
        "id": conversation.id,
        "channelName": conversation.channel.name,
        "provider": conversation.connection.provider if conversation.connection_id else None,
        "lifecycle": conversation.lifecycle,
        "createdAt": conversation.created_at.isoformat(),
        "lastActivityAt": conversation.last_activity_at.isoformat(),
        "topic": (first or "").replace("\n", " ")[:80],
        "handledBy": (operator.full_name or operator.email) if operator else None,
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


def _contact_username(conversation: Conversation) -> str:
    # Username живёт на identity подключения (у контакта их может быть несколько).
    # Только в detail-режиме — в списках это лишний запрос на каждый диалог.
    if not conversation.connection_id:
        return ""
    identity = ConnectionIdentity.objects.filter(
        connection_id=conversation.connection_id, contact_id=conversation.contact_id
    ).first()
    return identity.username if identity else ""


def _contact_email(conversation: Conversation) -> str:
    if (
        conversation.connection_id
        and conversation.connection.provider == IntegrationProvider.EMAIL
    ):
        return conversation.external_chat_id
    return ""


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
        .select_related("channel", "connection", "assigned_operator")
        .order_by("-last_activity_at")[:10]
    )


def conversation_payload(
    conversation: Conversation,
    *,
    with_messages: bool = False,
    last_read_id: int = 0,
    viewer_id: int | None = None,
) -> dict[str, object]:
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
            {
                "id": conversation.contact_id,
                "name": conversation.contact.name,
                "phone": conversation.contact.phone,
                "avatarUrl": conversation.contact.avatar_url,
                "description": conversation.contact.description,
                "company": conversation.contact.company,
                "city": conversation.contact.city,
                "email": _contact_email(conversation),
                "username": _contact_username(conversation) if with_messages else "",
            }
            if conversation.contact_id
            else None
        ),
        "supportIdentitySnapshot": _support_identity_snapshot(conversation, detailed=with_messages),
        "lifecycle": conversation.lifecycle,
        "controlMode": conversation.control_mode,
        "expectedResponder": conversation.expected_responder,
        "assignedOperatorId": conversation.assigned_operator_id,
        "assignedOperator": (
            {
                "id": conversation.assigned_operator_id,
                "name": (
                    conversation.assigned_operator.full_name
                    or conversation.assigned_operator.email
                ),
                "avatarUrl": user_avatar_url_in(conversation.assigned_operator, conversation.organization_id),
            }
            if conversation.assigned_operator_id
            else None
        ),
        "isAssignedToViewer": bool(
            viewer_id and conversation.assigned_operator_id == viewer_id
        ),
        "group": (
            {"id": conversation.group_id, "name": conversation.group.name, "color": conversation.group.color}
            if conversation.group_id
            else None
        ),
        # Дизайн-базлайн v2: приоритет, метки, заметка, архив.
        "priority": conversation.priority,
        "labels": [
            {"id": label.id, "name": label.name, "color": label.color}
            for label in conversation.labels.all()
        ],
        "note": conversation.note,
        "archivedAt": (
            conversation.archived_at.isoformat() if conversation.archived_at else None
        ),
        "lastActivityAt": conversation.last_activity_at.isoformat(),
        "createdAt": conversation.created_at.isoformat(),
    }
    if with_messages:
        payload["messages"] = [message_payload(m) for m in conversation.messages.select_related("author_user").order_by("created_at", "id")]
        history = _conversation_history(conversation)
        payload["history"] = [_history_item(c) for c in history]
    else:
        payload["lastMessage"] = message_payload(last) if last else None
        payload["pendingCount"] = _pending_count(conversation, last_read_id)
    return payload
