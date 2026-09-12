from __future__ import annotations

from zoneinfo import available_timezones

from django.urls import reverse

from chatballs.i18n import t
from chatballs.i18n.languages import LANGUAGES
from chatballs.identity.audit_catalog import (
    audit_action_label,
    audit_category,
    audit_category_label,
    audit_object_label,
    audit_result_label,
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
        # Пустая строка доезжает до интерфейса как есть: там это отдельный
        # пункт «Как в установке», а не отсутствие значения.
        "language": organization.language,
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


def administration_languages() -> list[dict[str, str]]:
    """Языки для выпадающего списка в «Организации».

    Подпись — на самом языке («Русский», «English»), а не переведённая:
    человек ищет в списке свой язык, и «Русский» он узнает, даже когда
    интерфейс сейчас английский.
    """

    return [{"code": code, "label": label} for code, label in LANGUAGES]


def audit_event_payload(event: AuditEvent) -> dict[str, object]:
    """Событие журнала. Отдаём и код действия, и подпись: подписи может не быть
    (тогда интерфейс показывает код), а код нужен для поиска в любом случае."""

    actor = event.actor
    category = audit_category(event.action)
    return {
        "id": event.id,
        "createdAt": event.created_at.isoformat(),
        "actorId": actor.id if actor is not None else None,
        "actor": ((actor.full_name or actor.email) if actor is not None else t("admin.actor_system")),
        "actorEmail": (actor.email if actor is not None else ""),
        "action": event.action,
        "actionLabel": audit_action_label(event.action),
        "category": category,
        "categoryLabel": audit_category_label(category),
        "object": audit_object_label(event.object_type, event.object_id),
        "objectType": event.object_type,
        "objectId": event.object_id,
        "result": event.result,
        "resultLabel": audit_result_label(event.result),
        "sourceIp": event.source_ip or "",
        "correlationId": event.correlation_id,
        "details": event.payload or {},
    }
