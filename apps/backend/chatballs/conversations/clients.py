"""Real clients list (contacts + their conversations).

A "client" is a Contact. Commerce data was removed with the sales domain
(ADR-HUB-0041) — no orders or revenue here.
"""

from __future__ import annotations

from django.db.models import Prefetch, Q

from chatballs.conversations.models import (
    ConnectionIdentity,
    Contact,
    Conversation,
    ControlMode,
    LifecycleState,
)
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
        "channel", "channel__product", "connection"
    ).order_by("-last_activity_at")
    identity_qs = ConnectionIdentity.objects.select_related("connection")
    contacts = Contact.objects.filter(organization_id=organization_id).prefetch_related(
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
        open_dialogs = 0
        for conversation in conversations:
            provider = conversation.connection.provider if conversation.connection_id else None
            if provider in PROVIDER_CODE:
                channels.add(PROVIDER_CODE[provider])
            if conversation.channel.product_id:
                products[conversation.channel.product.code] = conversation.channel.product.name
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
    ).select_related("channel", "channel__product", "connection")
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
        last = conversation.messages.order_by("-created_at").first()
        title = (last.text.replace("\n", " ")[:80] if last and last.text else conversation.channel.name)
        dialogs.append(
            {
                "id": conversation.id,
                "title": title,
                "channelName": conversation.channel.name,
                "provider": provider,
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
            "username": identity.username,
            "createdAt": identity.created_at.isoformat(),
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
    }
