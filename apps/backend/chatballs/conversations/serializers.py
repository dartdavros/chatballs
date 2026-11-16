from django.db.models import Count, Max, Q

from chatballs.conversations.access import conversation_access_payload
from chatballs.conversations.contact_avatars import contact_avatar_url_in
from chatballs.conversations.message_serializers import message_payload
from chatballs.conversations.models import (
    Conversation,
    Message,
    MessageAuthor,
    MessageKind,
    SystemEvent,
)
from chatballs.conversations.serializer_context import (
    _connection_identity,
    _contact_email,
    _contact_is_guest,
    _conversation_history,
    _history_item,
    _last_message,
)
from chatballs.conversations.site_fields import site_fields_payload
from chatballs.identity.avatars import user_avatar_url_in
from chatballs.integrations.features import features_payload


def last_messages_for(conversation_ids: list[int]) -> dict[int, Message]:
    """Последняя реплика каждого диалога страницы — одним запросом.

    Превью строки списка раньше спрашивалось на каждый диалог: тридцать строк
    инбокса стоили тридцати запросов, и обновление списка раз в четыре секунды
    множило их на число операторов.
    """
    if not conversation_ids:
        return {}
    rows = (
        Message.objects.filter(conversation_id__in=conversation_ids)
        .exclude(author_type=MessageAuthor.SYSTEM)
        .select_related("author_user", "email_transport", "externalagentdeliveryitem__delivery__request")
        .order_by("conversation_id", "-created_at", "-id")
        .distinct("conversation_id")
    )
    return {message.conversation_id: message for message in rows}


def pending_counts_for(conversation_ids: list[int], read_map: dict[int, int]) -> dict[int, int]:
    """Бейджи непрочитанных для страницы — двумя запросами вместо строки-на-строку.

    Считается хвост клиентских сообщений: те, что пришли после последнего
    ответа AI или оператора и которых просматривающий ещё не открывал.
    """
    if not conversation_ids:
        return {}
    answered = dict(
        Message.objects.filter(conversation_id__in=conversation_ids)
        .exclude(author_type=MessageAuthor.CONTACT)
        .exclude(system_event=SystemEvent.SITE_FIELDS_UPDATED)
        .values("conversation_id")
        .annotate(last_id=Max("id"))
        .values_list("conversation_id", "last_id")
    )
    tail = Q()
    for conversation_id in conversation_ids:
        threshold = max(read_map.get(conversation_id, 0), answered.get(conversation_id, 0))
        tail |= Q(conversation_id=conversation_id, id__gt=threshold)
    counts = (
        Message.objects.filter(author_type=MessageAuthor.CONTACT)
        .filter(tail)
        .values("conversation_id")
        .annotate(total=Count("id"))
        .values_list("conversation_id", "total")
    )
    return dict(counts)


def _pending_count(conversation: Conversation, last_read_id: int = 0) -> int:
    # Бейдж непрочитанных: хвост клиентских сообщений (после последнего ответа
    # AI/оператора), которые просматривающий ещё не открывал (id > отметки
    # прочтения). Открытие диалога двигает отметку — бейдж гаснет.
    count = 0
    for message in conversation.messages.exclude(system_event=SystemEvent.SITE_FIELDS_UPDATED).order_by("-created_at")[:50]:
        if message.author_type != MessageAuthor.CONTACT:
            break
        if message.id > last_read_id:
            count += 1
    return count


def conversation_payload(
    conversation: Conversation,
    *,
    detailed: bool = False,
    last_read_id: int = 0,
    viewer_id: int | None = None,
    last_message: Message | None = None,
    pending_count: int | None = None,
) -> dict[str, object]:
    """Карточка диалога.

    Сообщения в неё не входят ни в одном режиме: история — отдельная лента с
    собственным окном (`/messages/`), иначе открытие диалога с тысячей реплик
    тянуло бы их все, да ещё и на каждом обновлении карточки.
    """
    # Списку превью и бейдж считает страница целиком (last_messages_for,
    # pending_counts_for); поштучный расчёт остаётся для одиночных ответов.
    last = None if detailed else (last_message or _last_message(conversation))
    channel = conversation.channel
    identity = _connection_identity(conversation) if detailed and conversation.contact_id else None
    payload = {
        "id": conversation.id,
        "hasAgent": hasattr(channel, "ai_agent"),
        "channel": {
            "id": channel.id,
            "code": channel.code,
            "name": channel.name,
        },
        "connection": (
            {
                "id": conversation.connection_id,
                "provider": conversation.connection.provider,
                "name": conversation.connection.name,
                # Что разрешено в этой точке входа («Настройки → Голосовые и звонки»).
                **features_payload(conversation.connection),
            }
            if conversation.connection_id
            else None
        ),
        "contact": (
            {
                "id": conversation.contact_id,
                "name": conversation.contact.name,
                "phone": conversation.contact.phone,
                "avatarUrl": contact_avatar_url_in(
                    conversation.contact, conversation.organization_id
                ),
                "description": conversation.contact.description,
                "company": conversation.contact.company,
                "city": conversation.contact.city,
                "email": _contact_email(conversation),
                "username": identity.username if identity else "",
                # Для переменной {{client_name}} шаблонов ответов.
                **({"isGuest": _contact_is_guest(conversation.contact, identity)} if detailed else {}),
            }
            if conversation.contact_id
            else None
        ),
        "lifecycle": conversation.lifecycle,
        "controlMode": conversation.control_mode,
        "expectedResponder": conversation.expected_responder,
        "assignedOperatorId": conversation.assigned_operator_id,
        "assignmentVersion": conversation.assignment_version,
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
        "isParticipant": bool(getattr(conversation, "viewer_participates", False)),
        "isAssignedToViewer": bool(
            viewer_id and conversation.assigned_operator_id == viewer_id
        ),
        # Ожидание (макет «Очередь и уведомления», кадры Q3 и Q4): с какого
        # момента диалог ждёт человека и с какого — конкретного человека.
        # Считать «сколько осталось» клиент должен сам: минута на сервере и
        # минута на экране расходятся, и показывать замерший счётчик хуже, чем
        # не показывать никакого.
        "waitingSince": (
            conversation.waiting_since.isoformat() if conversation.waiting_since else None
        ),
        "assignedAt": (
            conversation.assigned_at.isoformat() if conversation.assigned_at else None
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
    if detailed:
        payload["siteFields"] = site_fields_payload(conversation.contact, integration_id=conversation.connection_id) if conversation.contact_id else []
        history = _conversation_history(conversation, viewer_id)
        payload["history"] = [_history_item(c) for c in history]
        # Запрос контакта мог уйти когда угодно — в загруженном окне истории его
        # может не быть, поэтому факт запроса считает сервер, а не лента.
        payload["contactRequested"] = conversation.messages.filter(
            kind=MessageKind.CONTACT_REQUEST
        ).exists()
        # Редактору ответа: включена ли помощь оператору у агента канала.
        # Право запроса сервер всё равно проверяет сам при каждом обращении.
        agent = getattr(channel, "ai_agent", None)
        payload["canReleaseToAi"] = _can_release_to_ai(conversation)
        payload["replyAssistanceEnabled"] = bool(agent and agent.assistance_enabled)
    else:
        payload["lastMessage"] = message_payload(last) if last else None
        payload["pendingCount"] = (
            pending_count if pending_count is not None else _pending_count(conversation, last_read_id)
        )
    if detailed:
        payload["access"] = conversation_access_payload(conversation, viewer_id)
        from chatballs.ai.external_agents.ui_projection import conversation_status

        payload["externalExecution"] = conversation_status(conversation)
    return payload


def _can_release_to_ai(conversation):
    from chatballs.identity.operation_modes import autonomous_allowed

    return autonomous_allowed(conversation.channel, organization=conversation.organization,
                              connection=conversation.connection)
