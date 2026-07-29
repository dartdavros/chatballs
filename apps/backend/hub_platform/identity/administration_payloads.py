from __future__ import annotations

from zoneinfo import available_timezones

from django.urls import reverse

from hub_platform.identity.models import AuditEvent, Organization
from hub_platform.subscriptions.models import Subscription, UsageCounter
from hub_platform.subscriptions.policy import get_effective_policy
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.models import OrganizationStorageUsage


QUOTA_LABELS = {
    "new_dialogs_per_period": "Новые диалоги",
    "managed_ai_credits": "AI-кредиты",
    "storage_bytes": "Хранилище",
}

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


def subscription_payload(context: TenantContext) -> dict[str, object]:
    subscription = Subscription.objects.select_related("plan_version__plan").get(
        organization_id=context.organization_id
    )
    policy = get_effective_policy(context)
    counters = {
        counter.quota_definition.key: counter.used_value
        for counter in UsageCounter.objects.select_related("quota_definition").filter(
            organization_id=context.organization_id,
            period__status="OPEN",
        )
    }
    storage = (
        OrganizationStorageUsage.objects.filter(
            organization_id=context.organization_id,
        )
        .values_list("bytes_used", flat=True)
        .first()
    )
    counters["storage_bytes"] = storage or 0
    quotas = [
        {
            "key": quota.key,
            "label": QUOTA_LABELS.get(quota.key, "Лимит"),
            "mode": quota.mode,
            "limit": quota.limit,
            "used": counters.get(quota.key, 0),
            "unit": quota.unit,
        }
        for quota in policy.quotas.values()
        if quota.key in QUOTA_LABELS
    ]
    quotas.sort(key=lambda item: str(item["label"]))
    return {
        "planCode": subscription.plan_version.plan.code,
        "planName": subscription.plan_version.plan.name,
        "status": subscription.status,
        "aiAgentQuantity": subscription.ai_agent_quantity,
        "monthlyChargeMinor": subscription.monthly_charge_minor,
        "currency": subscription.plan_version.currency,
        "periodStart": (
            subscription.current_period_start.isoformat()
            if subscription.current_period_start
            else None
        ),
        "periodEnd": (
            subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None
        ),
        "quotas": quotas,
    }


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
