"""Real clients list (contacts + their conversations).

A "client" is a Contact. Commerce data was removed with the sales domain
(ADR-CHATBALLS-0041) — no orders or revenue here.
"""

from __future__ import annotations

from django.db.models import (
    Count,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce

from chatballs.conversations.models import (
    ConnectionIdentity,
    Contact,
    ContactMerge,
    ControlMode,
    Conversation,
    LifecycleState,
)
from chatballs.i18n import t
from chatballs.identity.audit_catalog import (
    audit_action_label,
    audit_object_label,
    audit_result_label,
)
from chatballs.identity.avatars import user_avatar_url_in
from chatballs.identity.models import AuditEvent

# Короткие коды для UI (совпадают с фронтовыми справочниками).
PROVIDER_CODE = {
    "MAX": "MAX",
    "TELEGRAM": "TG",
    "WEB": "WEB",
    "EMAIL": "EMAIL",
}


def _actor_name(user) -> str:
    return (user.full_name or user.email) if user is not None else ""


def _mode(latest: Conversation) -> str:
    if latest.lifecycle != LifecycleState.OPEN:
        return "closed"
    if latest.control_mode == ControlMode.HUMAN:
        return "operator"
    if latest.control_mode == ControlMode.AI:
        return "ai"
    return "wait"


# Провайдер подключения по короткому коду канала из фильтра списка (кадр K1).
PROVIDER_BY_CODE = {code: provider for provider, code in PROVIDER_CODE.items()}


def _client_counts(*, lifecycle: str | None = None) -> Subquery:
    """Число диалогов контакта отдельным подзапросом.

    Через join-агрегат считать нельзя: фильтры списка (агент, канал) идут по
    той же связи и урезали бы счётчик до отфильтрованных строк.
    """
    conversations = (
        Conversation.objects.filter(contact_id=OuterRef("pk"))
        .order_by()
        .values("contact_id")
        .annotate(total=Count("id"))
        .values("total")
    )
    if lifecycle:
        conversations = (
            Conversation.objects.filter(contact_id=OuterRef("pk"), lifecycle=lifecycle)
            .order_by()
            .values("contact_id")
            .annotate(total=Count("id"))
            .values("total")
        )
    return Coalesce(Subquery(conversations, output_field=IntegerField()), Value(0))


def clients_queryset(organization_id: int, params) -> QuerySet[Contact]:
    """Список контактов (кадры K1/K2): фильтры, поиск и порядок — на сервере.

    Клиент — контакт, который писал: у него есть хотя бы один диалог.
    """
    conversation_qs = Conversation.objects.select_related(
        "channel", "connection", "assigned_operator"
    ).order_by("-last_activity_at")
    identity_qs = ConnectionIdentity.objects.select_related("connection")
    contacts = (
        Contact.objects.filter(organization_id=organization_id, merged_into__isnull=True)
        .annotate(
            last_activity=Subquery(
                Conversation.objects.filter(contact_id=OuterRef("pk"))
                .order_by("-last_activity_at")
                .values("last_activity_at")[:1]
            ),
            open_dialogs_count=_client_counts(lifecycle=LifecycleState.OPEN),
            total_dialogs_count=_client_counts(),
        )
        .filter(last_activity__isnull=False)
        # Связанное подтягивается уже для страницы: prefetch выполняется после
        # среза, а не по всей организации.
        .prefetch_related(
            Prefetch("conversations", queryset=conversation_qs),
            Prefetch("identities", queryset=identity_qs),
        )
    )
    query = params.get("q", "").strip()
    if query:
        contacts = contacts.filter(
            Q(name__icontains=query)
            | Q(phone__icontains=query)
            | Q(identities__username__icontains=query)
            | Q(identities__external_user_id__icontains=query)
        )
    agents = [value for value in params.getlist("agent") if value.isdigit()]
    if agents:
        contacts = contacts.filter(conversations__channel_id__in=agents)
    providers = [
        PROVIDER_BY_CODE[code] for code in params.getlist("channel") if code in PROVIDER_BY_CODE
    ]
    if providers:
        contacts = contacts.filter(conversations__connection__provider__in=providers)
    if params.get("open") == "1":
        contacts = contacts.filter(open_dialogs_count__gt=0)
    field = "open_dialogs_count" if params.get("sort") == "open" else "last_activity"
    ascending = params.get("dir") == "asc"
    return contacts.distinct().order_by(f"{'' if ascending else '-'}{field}", "-id")


def client_row(contact: Contact) -> dict:
    """Строка списка контактов. Связанные диалоги и identity приходят из prefetch."""
    conversations = list(contact.conversations.all())
    channels: set[str] = set()
    agents: dict[int, dict[str, object]] = {}
    for conversation in conversations:
        provider = conversation.connection.provider if conversation.connection_id else None
        if provider in PROVIDER_CODE:
            channels.add(PROVIDER_CODE[provider])
        # Агент = карточка канала обработки: по нему фильтруется список (кадр K1).
        agents.setdefault(
            conversation.channel_id,
            {"id": conversation.channel_id, "code": conversation.channel.code, "name": conversation.channel.name},
        )
    latest = conversations[0]
    return {
        "id": contact.id,
        "cid": f"CUS-{contact.id}",
        "name": contact.name or t("conversations.guest"),
        # Признак анонимного посетителя: интерфейс красит его аватар иначе.
        # Раньше он выводился из самой подписи регуляркой по слову «Гость» —
        # на другом языке это перестало бы работать.
        "isGuest": not contact.name,
        "phone": contact.phone,
        "avatarUrl": contact.avatar_url,
        "email": next(
            (
                identity.external_user_id
                for identity in contact.identities.all()
                if identity.connection.provider == "EMAIL"
            ),
            "",
        ),
        # Первый непустой @логин среди identity каналов (остальные — в карточке).
        "username": next((identity.username for identity in contact.identities.all() if identity.username), ""),
        "channels": sorted(channels),
        "openDialogs": contact.open_dialogs_count,
        "totalDialogs": contact.total_dialogs_count,
        "lastActivityAt": latest.last_activity_at.isoformat(),
        "mode": _mode(latest),
        # Колонка «Последний диалог» (кадр K1): кто ведёт — агент или сотрудник.
        "lastAgentName": latest.channel.name,
        "lastAgentCode": latest.channel.code,
        "lastAssignee": _actor_name(latest.assigned_operator),
        "agents": sorted(agents.values(), key=lambda item: str(item["name"])),
    }


def _dialog_status(conversation: Conversation) -> str:
    return {"closed": "Закрыт", "operator": "Оператор", "ai": "AI", "wait": "Ждёт оператора"}[_mode(conversation)]


def client_detail(organization_id: int, contact_id: int) -> dict:
    contact = Contact.objects.get(organization_id=organization_id, id=contact_id)
    conversation_qs = Conversation.objects.filter(
        organization_id=organization_id, contact=contact
    ).select_related("channel", "connection", "group", "assigned_operator", "note_author")
    conversations = list(conversation_qs.order_by("-last_activity_at"))
    if not conversations:
        raise Contact.DoesNotExist

    channels: set[str] = set()
    open_dialogs = 0
    dialogs: list[dict] = []
    for conversation in conversations:
        provider = conversation.connection.provider if conversation.connection_id else None
        if provider in PROVIDER_CODE:
            channels.add(PROVIDER_CODE[provider])
        if conversation.lifecycle == LifecycleState.OPEN:
            open_dialogs += 1
        # Тема диалога — первое сообщение, превью — последнее (кадр K4).
        first = conversation.messages.order_by("created_at").first()
        last = conversation.messages.order_by("-created_at").first()
        title = (first.text.replace("\n", " ")[:80] if first and first.text else conversation.channel.name)
        preview = (last.text.replace("\n", " ")[:120] if last and last.text else "")
        dialogs.append(
            {
                "id": conversation.id,
                "title": title,
                "preview": preview,
                "channelName": conversation.channel.name,
                "agentName": conversation.channel.name,
                "agentId": conversation.channel_id,
                "agentCode": conversation.channel.code,
                "groupName": conversation.group.name if conversation.group_id else "",
                "groupColor": conversation.group.color if conversation.group_id else "",
                "assignee": _actor_name(conversation.assigned_operator),
                "assigneeAvatarUrl": user_avatar_url_in(conversation.assigned_operator, organization_id),
                "note": conversation.note,
                "noteAuthor": _actor_name(conversation.note_author),
                "noteUpdatedAt": conversation.note_updated_at.isoformat() if conversation.note_updated_at else None,
                "provider": provider,
                "mode": _mode(conversation),
                "status": _dialog_status(conversation),
                "active": conversation.lifecycle == LifecycleState.OPEN,
                "lastActivityAt": conversation.last_activity_at.isoformat(),
            }
        )

    identity_qs = contact.identities.select_related("connection")
    identities = [
        {
            "provider": identity.connection.provider,
            "value": (
                identity.external_user_id
                if identity.connection.provider == "EMAIL"
                else identity.display_name or identity.external_user_id
            ),
            "externalUserId": identity.external_user_id,
            "username": identity.username,
            "createdAt": identity.created_at.isoformat(),
            # Подтверждённой считается идентичность, отдавшая телефон (ADR-CHATBALLS-0006).
            "phoneVerifiedAt": identity.phone_verified_at.isoformat() if identity.phone_verified_at else None,
        }
        for identity in identity_qs.order_by("created_at")
    ]

    # Активность из жизненного цикла диалогов (created/closed) — реальные события.
    activity: list[dict] = []
    for conversation in conversations:
        activity.append({"type": "created", "title": f"Диалог · {conversation.channel.name}", "at": conversation.created_at.isoformat()})
        if conversation.lifecycle == LifecycleState.CLOSED:
            activity.append({"type": "closed", "title": f"Диалог закрыт · {conversation.channel.name}", "at": conversation.last_activity_at.isoformat()})
    activity.sort(key=lambda item: item["at"], reverse=True)

    conversation_ids = [str(conversation.id) for conversation in conversations]
    audit = []
    audit_scope = Q(object_type="Conversation", object_id__in=conversation_ids)
    audit_scope |= Q(object_type="Contact", object_id=str(contact_id))
    audit_qs = (
        AuditEvent.objects.filter(organization_id=organization_id)
        .filter(audit_scope)
        .select_related("actor")
        .order_by("-created_at")[:20]
    )
    for event in audit_qs:
        audit.append(
            {
                "time": event.created_at.isoformat(),
                # Подписи, типы объектов и результаты — из общего каталога
                # журнала действий: коды действий и enum-значения на экран
                # карточки не попадают. Пустая подпись означает «её ещё нет»,
                # тогда показываем код — как в журнале.
                "action": audit_action_label(event.action) or event.action,
                "object": audit_object_label(event.object_type, event.object_id),
                "actor": (event.actor.full_name or event.actor.email) if event.actor_id else "Система",
                "result": audit_result_label(event.result),
            }
        )

    return {
        "id": contact.id,
        "cid": f"CUS-{contact.id}",
        "name": contact.name or t("conversations.guest"),
        # Признак анонимного посетителя: интерфейс красит его аватар иначе.
        # Раньше он выводился из самой подписи регуляркой по слову «Гость» —
        # на другом языке это перестало бы работать.
        "isGuest": not contact.name,
        "phone": contact.phone,
        "avatarUrl": contact.avatar_url,
        # Поля карточки из чата (описание, компания, город).
        "description": contact.description,
        "company": contact.company,
        "city": contact.city,
        "email": next(
            (
                identity.external_user_id
                for identity in identity_qs
                if identity.connection.provider == "EMAIL"
            ),
            "",
        ),
        "channels": sorted(channels),
        "openDialogs": open_dialogs,
        "totalDialogs": len(conversations),
        "firstContactAt": contact.created_at.isoformat(),
        "lastActivityAt": conversations[0].last_activity_at.isoformat() if conversations else contact.created_at.isoformat(),
        "dialogs": dialogs,
        "identities": identities,
        "activity": activity[:8],
        "audit": audit,
        "duplicate": _duplicate_candidate(organization_id, contact),
        "merges": _merges(organization_id, contact),
    }


def _merges(organization_id: int, contact: Contact) -> list[dict]:
    """Действующие объединения этого контакта — их можно разъединить."""
    rows = (
        ContactMerge.objects.filter(organization_id=organization_id, target=contact, reverted_at__isnull=True)
        .select_related("source", "actor")
        .order_by("-created_at")
    )
    return [
        {
            "id": row.id,
            "sourceId": row.source_id,
            "sourceName": row.source.name or t("conversations.guest"),
            "sourceCid": f"CUS-{row.source_id}",
            "reason": row.reason,
            "actor": _actor_name(row.actor),
            "at": row.created_at.isoformat(),
            "identities": len(row.moved_identity_ids),
            "conversations": len(row.moved_conversation_ids),
        }
        for row in rows
    ]


def _duplicate_candidate(organization_id: int, contact: Contact) -> dict | None:
    """Другой контакт с тем же телефоном. Автоматически ничего не объединяем
    (ADR-CHATBALLS-0006) — это только предложение владельцу."""
    if not contact.phone:
        return None
    other = (
        Contact.objects.filter(organization_id=organization_id, phone=contact.phone, merged_into__isnull=True)
        .exclude(id=contact.id)
        .prefetch_related("identities__connection", "conversations")
        .first()
    )
    if other is None:
        return None
    identities = list(other.identities.all())
    return {
        "id": other.id,
        "cid": f"CUS-{other.id}",
        "name": other.name or t("conversations.guest"),
        "isGuest": not other.name,
        "avatarUrl": other.avatar_url,
        "dialogs": other.conversations.count(),
        "sources": sorted({identity.connection.provider for identity in identities}),
        "phone": other.phone,
        # Однозначным совпадение считается, только если телефон подтверждён
        # подключением хотя бы у одной стороны (ADR-CHATBALLS-0006).
        "phoneVerified": any(identity.phone_verified_at is not None for identity in identities),
    }
