"""Real clients list (contacts + their conversations).

A "client" is a Contact. Commerce data was removed with the sales domain
(ADR-HUB-0041) — no orders or revenue here.
"""

from __future__ import annotations

from django.db.models import Prefetch, Q

from chatballs.conversations.models import (
    ConnectionIdentity,
    Contact,
    ContactMerge,
    Conversation,
    ControlMode,
    LifecycleState,
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

# Понятные подписи для аудита диалогов.
AUDIT_LABELS = {
    "conversations.claimed": "Перехват оператором",
    "conversations.released_to_ai": "Возврат к AI",
    "conversations.returned_to_queue": "Возврат в очередь",
    "conversations.closed": "Диалог закрыт",
    "conversations.marked_spam": "Диалог помечен как спам",
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


def clients_overview(organization_id: int) -> list[dict]:
    conversation_qs = Conversation.objects.select_related(
        "channel", "channel__product", "connection", "assigned_operator"
    ).order_by("-last_activity_at")
    identity_qs = ConnectionIdentity.objects.select_related("connection")
    contacts = Contact.objects.filter(organization_id=organization_id, merged_into__isnull=True).prefetch_related(
        Prefetch(
            "conversations",
            queryset=conversation_qs,
        ),
        Prefetch("identities", queryset=identity_qs),
    )
    rows: list[dict] = []
    for contact in contacts:
        conversations = list(contact.conversations.all())
        if not conversations:
            continue  # клиенты — те, кто писал
        channels: set[str] = set()
        products: dict[str, str] = {}
        agents: dict[int, dict[str, object]] = {}
        open_dialogs = 0
        for conversation in conversations:
            provider = conversation.connection.provider if conversation.connection_id else None
            if provider in PROVIDER_CODE:
                channels.add(PROVIDER_CODE[provider])
            if conversation.channel.product_id:
                products[conversation.channel.product.code] = conversation.channel.product.name
            # Агент = карточка канала обработки: по нему фильтруется список (кадр K1).
            agents.setdefault(
                conversation.channel_id,
                {"id": conversation.channel_id, "code": conversation.channel.code, "name": conversation.channel.name},
            )
            if conversation.lifecycle == LifecycleState.OPEN:
                open_dialogs += 1
        latest = conversations[0]
        rows.append(
            {
                "id": contact.id,
                "cid": f"CUS-{contact.id}",
                "name": contact.name or "Гость",
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
                "products": [{"code": code, "name": name} for code, name in sorted(products.items())],
                "openDialogs": open_dialogs,
                "totalDialogs": len(conversations),
                "lastActivityAt": latest.last_activity_at.isoformat(),
                "mode": _mode(latest),
                # Колонка «Последний диалог» (кадр K1): кто ведёт — агент или сотрудник.
                "lastAgentName": latest.channel.name,
                "lastAgentCode": latest.channel.code,
                "lastAssignee": _actor_name(latest.assigned_operator),
                "agents": sorted(agents.values(), key=lambda item: str(item["name"])),
            }
        )
    rows.sort(key=lambda row: row["lastActivityAt"], reverse=True)
    return rows


def _dialog_status(conversation: Conversation) -> str:
    return {"closed": "Закрыт", "operator": "Оператор", "ai": "AI", "wait": "Ждёт оператора"}[_mode(conversation)]


def client_detail(organization_id: int, contact_id: int) -> dict:
    contact = Contact.objects.get(organization_id=organization_id, id=contact_id)
    conversation_qs = Conversation.objects.filter(
        organization_id=organization_id, contact=contact
    ).select_related("channel", "channel__product", "connection", "group", "assigned_operator", "note_author")
    conversations = list(conversation_qs.order_by("-last_activity_at"))
    if not conversations:
        raise Contact.DoesNotExist

    channels: set[str] = set()
    products: dict[str, str] = {}
    open_dialogs = 0
    dialogs: list[dict] = []
    for conversation in conversations:
        provider = conversation.connection.provider if conversation.connection_id else None
        if provider in PROVIDER_CODE:
            channels.add(PROVIDER_CODE[provider])
        if conversation.channel.product_id:
            products[conversation.channel.product.code] = conversation.channel.product.name
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
            # Подтверждённой считается идентичность, отдавшая телефон (ADR-HUB-0006).
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
                "action": AUDIT_LABELS.get(event.action, event.action),
                "object": f"{event.object_type} {event.object_id}".strip(),
                "actor": (event.actor.full_name or event.actor.email) if event.actor_id else "система",
                "result": event.result,
            }
        )

    return {
        "id": contact.id,
        "cid": f"CUS-{contact.id}",
        "name": contact.name or "Гость",
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
        "products": [{"code": code, "name": name} for code, name in sorted(products.items())],
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
            "sourceName": row.source.name or "Гость",
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
    (ADR-HUB-0006) — это только предложение владельцу."""
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
        "name": other.name or "Гость",
        "avatarUrl": other.avatar_url,
        "dialogs": other.conversations.count(),
        "sources": sorted({identity.connection.provider for identity in identities}),
        "phone": other.phone,
        # Однозначным совпадение считается, только если телефон подтверждён
        # подключением хотя бы у одной стороны (ADR-HUB-0006).
        "phoneVerified": any(identity.phone_verified_at is not None for identity in identities),
    }
