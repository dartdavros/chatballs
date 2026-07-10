"""Real clients list for the sales department (contacts + their conversations).

A "client" is a Contact. Orders/revenue have no domain in Hub yet, so they are
reported as 0 and shown as "—" in the UI — no fabricated numbers.
"""

from __future__ import annotations

from django.db.models import Prefetch, Q

from django.db.models import Count, Sum

from hub_platform.conversations.models import (
    Contact,
    Conversation,
    ControlMode,
    LifecycleState,
)
from hub_platform.identity.models import AuditEvent
from hub_platform.orders.models import Order, PaymentStatus

# Короткие коды для UI (совпадают с фронтовыми справочниками).
PROVIDER_CODE = {"MAX": "MAX", "TELEGRAM": "TG", "WEB": "WEB"}
PRODUCT_CODE = {"firepage": "FP", "foxray": "FX"}

# Понятные подписи для аудита диалогов.
AUDIT_LABELS = {
    "conversations.claimed": "Перехват оператором",
    "conversations.released_to_ai": "Возврат к AI",
    "conversations.returned_to_queue": "Возврат в очередь",
    "conversations.closed": "Диалог закрыт",
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
    contacts = Contact.objects.filter(organization_id=organization_id).prefetch_related(
        Prefetch(
            "conversations",
            queryset=Conversation.objects.select_related("channel", "channel__product", "connection").order_by("-last_activity_at"),
        )
    )
    paid_by_contact = {
        row["contact_id"]: row
        for row in Order.objects.filter(organization_id=organization_id, payment_status=PaymentStatus.PAID)
        .values("contact_id")
        .annotate(n=Count("id"), total=Sum("amount_minor"))
    }
    rows: list[dict] = []
    for contact in contacts:
        conversations = list(contact.conversations.all())
        if not conversations:
            continue  # клиенты — те, кто писал
        channels: set[str] = set()
        products: set[str] = set()
        open_dialogs = 0
        for conversation in conversations:
            provider = conversation.connection.provider if conversation.connection_id else None
            if provider in PROVIDER_CODE:
                channels.add(PROVIDER_CODE[provider])
            if conversation.channel.product_id and conversation.channel.product.code in PRODUCT_CODE:
                products.add(PRODUCT_CODE[conversation.channel.product.code])
            if conversation.lifecycle == LifecycleState.OPEN:
                open_dialogs += 1
        latest = conversations[0]
        paid = paid_by_contact.get(contact.id)
        rows.append(
            {
                "id": contact.id,
                "cid": f"CUS-{contact.id}",
                "name": contact.name or "Гость",
                "channels": sorted(channels),
                "products": sorted(products),
                "openDialogs": open_dialogs,
                "totalDialogs": len(conversations),
                "lastActivityAt": latest.last_activity_at.isoformat(),
                "mode": _mode(latest),
                "orders": paid["n"] if paid else 0,
                "total": (paid["total"] or 0) if paid else 0,
            }
        )
    rows.sort(key=lambda row: row["lastActivityAt"], reverse=True)
    return rows


def _dialog_status(conversation: Conversation) -> str:
    return {"closed": "Закрыт", "operator": "Оператор", "ai": "AI", "wait": "Ждёт оператора"}[_mode(conversation)]


def client_detail(organization_id: int, contact_id: int) -> dict:
    contact = Contact.objects.get(organization_id=organization_id, id=contact_id)
    conversations = list(
        Conversation.objects.filter(organization_id=organization_id, contact=contact)
        .select_related("channel", "channel__product", "connection")
        .order_by("-last_activity_at")
    )

    channels: set[str] = set()
    products: set[str] = set()
    open_dialogs = 0
    dialogs: list[dict] = []
    for conversation in conversations:
        provider = conversation.connection.provider if conversation.connection_id else None
        if provider in PROVIDER_CODE:
            channels.add(PROVIDER_CODE[provider])
        if conversation.channel.product_id and conversation.channel.product.code in PRODUCT_CODE:
            products.add(PRODUCT_CODE[conversation.channel.product.code])
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

    identities = [
        {
            "provider": identity.connection.provider,
            "value": identity.display_name or identity.external_user_id,
            "username": identity.username,
            "createdAt": identity.created_at.isoformat(),
        }
        for identity in contact.identities.select_related("connection").order_by("created_at")
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
    audit_qs = (
        AuditEvent.objects.filter(organization_id=organization_id)
        .filter(Q(object_type="Conversation", object_id__in=conversation_ids) | Q(object_type="Contact", object_id=str(contact_id)))
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

    orders = [
        {
            "id": order.id,
            "code": order.code,
            "product": order.product.name if order.product_id else "—",
            "amountMinor": order.amount_minor,
            "currency": order.currency,
            "paymentStatus": order.payment_status,
            "fulfillmentStatus": order.fulfillment_status,
            "createdAt": order.created_at.isoformat(),
        }
        for order in Order.objects.filter(organization_id=organization_id, contact=contact).select_related("product").order_by("-created_at")
    ]
    paid_total = sum(order["amountMinor"] for order in orders if order["paymentStatus"] == PaymentStatus.PAID)

    return {
        "id": contact.id,
        "cid": f"CUS-{contact.id}",
        "name": contact.name or "Гость",
        "phone": contact.phone,
        "channels": sorted(channels),
        "products": sorted(products),
        "openDialogs": open_dialogs,
        "totalDialogs": len(conversations),
        "ordersCount": len([order for order in orders if order["paymentStatus"] == PaymentStatus.PAID]),
        "purchasesMinor": paid_total,
        "firstContactAt": contact.created_at.isoformat(),
        "lastActivityAt": conversations[0].last_activity_at.isoformat() if conversations else contact.created_at.isoformat(),
        "dialogs": dialogs,
        "identities": identities,
        "orders": orders,
        "activity": activity[:8],
        "audit": audit,
    }
