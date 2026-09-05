from __future__ import annotations

from zoneinfo import available_timezones

from django.urls import reverse

from chatballs.identity.models import AuditEvent, Organization


AUDIT_ACTION_LABELS = {
    "identity.profile_updated": "Изменён профиль сотрудника",
    "identity.profile_password_changed": "Изменён пароль",
    "identity.employee_created": "Добавлен сотрудник",
    "identity.employee_blocked": "Сотрудник заблокирован",
    "identity.employee_unblocked": "Сотрудник разблокирован",
    "identity.ownership_transferred": "Передано владение организацией",
    "identity.access_profile_created": "Создан профиль доступа",
    "identity.access_profile_updated": "Изменён профиль доступа",
    "identity.access_assignment_created": "Назначен доступ сотруднику",
    "identity.access_assignment_revoked": "Отозван доступ сотрудника",
    "administration.organization_updated": "Изменены данные организации",
    "administration.logo_updated": "Изменён логотип организации",
    "administration.logo_deleted": "Удалён логотип организации",
    "products.product_created": "Добавлен продукт",
    "products.product_updated": "Изменён продукт",
    "products.product_active": "Продукт включён",
    "products.product_disabled": "Продукт отключён",
    "integrations.integration_created": "Добавлена интеграция",
    "integrations.integration_updated": "Изменена интеграция",
    "integrations.integration_deleted": "Удалена интеграция",
    "channels.channel_created": "Создан канал",
    "channels.channel_updated": "Изменён канал",
    "channels.channel_deleted": "Удалён канал",
    "ai.knowledge_created": "Добавлено знание",
    "ai.knowledge_updated": "Изменено знание",
    "ai.knowledge_deleted": "Удалено знание",
}

AUDIT_RESULT_LABELS = {
    "SUCCESS": "Выполнено",
    "DENIED": "Отклонено",
    "FAILED": "Ошибка",
}


def organization_settings_payload(organization: Organization) -> dict[str, object]:
    return {
        "name": organization.name,
        "timezone": organization.timezone,
        "currency": organization.currency,
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
    actor = event.actor
    return {
        "id": event.id,
        "createdAt": event.created_at.isoformat(),
        "actor": ((actor.full_name or actor.email) if actor is not None else "Система"),
        "action": AUDIT_ACTION_LABELS.get(event.action, "Системное действие"),
        "result": event.result,
        "resultLabel": AUDIT_RESULT_LABELS.get(event.result, "Неизвестно"),
    }
