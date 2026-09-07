from __future__ import annotations

# Возможности как словарь операций backend'а (ADR-HUB-0041, SPEC-HUB-0031 §3).
# Права выводятся ТОЛЬКО из роли: OWNER и ADMIN идентичны и получают всё;
# EMPLOYEE получает фиксированный набор для работы в чате. Профили доступа,
# scope-модель и отделы упразднены (ADR-HUB-0043).

ALL_CAPABILITIES: frozenset[str] = frozenset(
    {
        "company.view",
        "company.manage",
        "employees.view",
        "employees.manage",
        "groups.manage",
        "channels.view",
        "channels.manage",
        "ai.view",
        "ai.manage",
        "ai.publish",
        "integrations.view",
        "integrations.manage",
        "secrets.manage",
        "settings.view",
        "settings.manage",
        "audit.view",
        "conversations.view",
        "conversations.operate",
        "conversations.call",
        "customers.view",
        "customers.manage",
        "support.view",
        "support.operate",
        "notifications.manage",
        "employees.manage_privileged",
        "ownership.transfer",
    }
)

# Сотрудник работает в одном окне — чате: диалоги, звонки, карточка контакта.
EMPLOYEE_CAPABILITIES: frozenset[str] = frozenset(
    {
        "conversations.view",
        "conversations.operate",
        "conversations.call",
        "customers.view",
        "support.view",
        "support.operate",
    }
)

# Операции, доступные только владельцу (SPEC-HUB-0031 §3: передача владения).
OWNER_ONLY_CAPABILITIES: frozenset[str] = frozenset({"ownership.transfer"})
