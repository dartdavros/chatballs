from __future__ import annotations

from zoneinfo import available_timezones

from django.urls import reverse

from chatballs.identity.audit_catalog import (
    AUDIT_RESULT_LABELS,
    audit_action_label,
    audit_category,
    audit_category_label,
    audit_object_label,
)
from chatballs.identity.models import AuditEvent, Organization


ORGANIZATION_CHANGE_ACTIONS = (
    "administration.organization_updated",
    "administration.logo_updated",
    "administration.logo_deleted",
)


def organization_updated_at(organization: Organization) -> str | None:
    """Когда настройки организации сохраняли в последний раз (кадр N1:
    «Сохранено 2 сен, 14:12»). Берём из журнала аудита — отдельного поля
    в модели нет."""
    event = (
        AuditEvent.objects.filter(
            organization=organization,
            action__in=ORGANIZATION_CHANGE_ACTIONS,
            result="SUCCESS",
        )
        .order_by("-created_at")
        .values_list("created_at", flat=True)
        .first()
    )
    return event.isoformat() if event else None


def organization_settings_payload(organization: Organization) -> dict[str, object]:
    return {
        "name": organization.name,
        "timezone": organization.timezone,
        "currency": organization.currency,
        "updatedAt": organization_updated_at(organization),
        "logoUrl": (
            reverse(
                "organization-logo",
                kwargs={"organization_public_id": organization.public_id},
            )
            if organization.logo
            else None
        ),
    }


def administration_timezones() -> list[str]:
    return sorted(available_timezones())


def audit_event_payload(event: AuditEvent) -> dict[str, object]:
    """Событие журнала. Отдаём и код действия, и подпись: подписи может не быть
    (тогда интерфейс показывает код), а код нужен для поиска в любом случае."""

    actor = event.actor
    category = audit_category(event.action)
    return {
        "id": event.id,
        "createdAt": event.created_at.isoformat(),
        "actorId": actor.id if actor is not None else None,
        "actor": ((actor.full_name or actor.email) if actor is not None else "Система"),
        "actorEmail": (actor.email if actor is not None else ""),
        "action": event.action,
        "actionLabel": audit_action_label(event.action),
        "category": category,
        "categoryLabel": audit_category_label(category),
        "object": audit_object_label(event.object_type, event.object_id),
        "objectType": event.object_type,
        "objectId": event.object_id,
        "result": event.result,
        "resultLabel": AUDIT_RESULT_LABELS.get(event.result, "Неизвестно"),
        "sourceIp": event.source_ip or "",
        "correlationId": event.correlation_id,
        "details": event.payload or {},
    }
