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
    "integrations.integration_created": "Добавлена интеграция",
    "integrations.integration_updated": "Изменена интеграция",
    "integrations.integration_deleted": "Удалена интеграция",
    "channels.channel_created": "Создан канал",
    "channels.channel_updated": "Изменён канал",
    "channels.channel_deleted": "Удалён канал",
    "ai.knowledge_created": "Добавлено знание",
    "ai.knowledge_updated": "Изменено знание",
    "ai.knowledge_deleted": "Удалено знание",
    "contacts.merged": "Объединение контактов",
    "contacts.unmerged": "Разъединение контактов",
}

AUDIT_RESULT_LABELS = {
    "SUCCESS": "Выполнено",
    "DENIED": "Отклонено",
    "FAILED": "Ошибка",
}


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
    actor = event.actor
    return {
        "id": event.id,
        "createdAt": event.created_at.isoformat(),
        "actor": ((actor.full_name or actor.email) if actor is not None else "Система"),
        "action": AUDIT_ACTION_LABELS.get(event.action, "Системное действие"),
        "result": event.result,
        "resultLabel": AUDIT_RESULT_LABELS.get(event.result, "Неизвестно"),
    }
