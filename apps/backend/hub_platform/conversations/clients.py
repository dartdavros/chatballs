"""Real clients list for the sales department (contacts + their conversations).

A "client" is a Contact. Orders/revenue have no domain in Hub yet, so they are
reported as 0 and shown as "—" in the UI — no fabricated numbers.
"""

from __future__ import annotations

from django.db.models import Prefetch

from hub_platform.conversations.models import (
    Contact,
    Conversation,
    ControlMode,
    LifecycleState,
)

# Короткие коды для UI (совпадают с фронтовыми справочниками).
PROVIDER_CODE = {"MAX": "MAX", "TELEGRAM": "TG", "WEB": "WEB"}
PRODUCT_CODE = {"firepage": "FP", "foxray": "FX"}


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
                # Домена заказов нет — честные нули, в UI это «—».
                "orders": 0,
                "total": 0,
            }
        )
    rows.sort(key=lambda row: row["lastActivityAt"], reverse=True)
    return rows
