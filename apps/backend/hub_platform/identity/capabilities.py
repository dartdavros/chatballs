from __future__ import annotations

from dataclasses import dataclass


class ScopeType:
    ORGANIZATION = "ORGANIZATION"
    DEPARTMENT = "DEPARTMENT"


@dataclass(frozen=True, slots=True)
class CapabilitySpec:
    code: str
    name: str
    description: str
    allowed_scopes: frozenset[str]
    assignable: bool = True
    protected: bool = False


_ALL_SCOPES = frozenset({ScopeType.ORGANIZATION, ScopeType.DEPARTMENT})
_ORGANIZATION_ONLY = frozenset({ScopeType.ORGANIZATION})


def _capability(
    code: str,
    name: str,
    *,
    scopes: frozenset[str] = _ALL_SCOPES,
    assignable: bool = True,
    protected: bool = False,
) -> CapabilitySpec:
    return CapabilitySpec(
        code=code,
        name=name,
        description=name,
        allowed_scopes=scopes,
        assignable=assignable,
        protected=protected,
    )


# SPEC-HUB-0017 §5.2. The registry is application code, never database data.
CAPABILITY_REGISTRY = {
    item.code: item
    for item in (
        _capability("company.view", "Просмотр компании", scopes=_ORGANIZATION_ONLY),
        _capability("company.manage", "Управление компанией", scopes=_ORGANIZATION_ONLY),
        _capability("departments.view", "Просмотр отделов"),
        _capability("departments.manage", "Управление отделами", scopes=_ORGANIZATION_ONLY),
        _capability("employees.view", "Просмотр сотрудников"),
        _capability("employees.manage", "Управление сотрудниками", scopes=_ORGANIZATION_ONLY),
        _capability(
            "employees.manage_privileged",
            "Управление привилегированными сотрудниками",
            scopes=_ORGANIZATION_ONLY,
            assignable=False,
            protected=True,
        ),
        _capability(
            "ownership.transfer",
            "Передача владения",
            scopes=_ORGANIZATION_ONLY,
            assignable=False,
            protected=True,
        ),
        _capability("products.view", "Просмотр продуктов"),
        _capability("products.manage", "Управление продуктами"),
        _capability("ai.view", "Просмотр агентов", scopes=_ORGANIZATION_ONLY),
        _capability("ai.manage", "Настройка агентов", scopes=_ORGANIZATION_ONLY),
        _capability("ai.publish", "Публикация агентов", scopes=_ORGANIZATION_ONLY),
        _capability("integrations.view", "Просмотр интеграций", scopes=_ORGANIZATION_ONLY),
        _capability("integrations.manage", "Управление интеграциями", scopes=_ORGANIZATION_ONLY),
        _capability("secrets.manage", "Управление секретами", scopes=_ORGANIZATION_ONLY),
        _capability("settings.view", "Просмотр настроек", scopes=_ORGANIZATION_ONLY),
        _capability("settings.manage", "Управление настройками", scopes=_ORGANIZATION_ONLY),
        _capability("audit.view", "Просмотр аудита", scopes=_ORGANIZATION_ONLY),
        _capability("conversations.view", "Просмотр диалогов"),
        _capability("conversations.operate", "Работа с диалогами"),
        _capability("conversations.call", "Звонки"),
        _capability("customers.view", "Просмотр клиентов"),
        _capability("customers.manage", "Управление клиентами"),
        _capability("sales.view", "Просмотр продаж"),
        _capability("sales.operate", "Работа с продажами"),
        _capability("sales.correct", "Корректировка продаж"),
        _capability("sales_sources.manage", "Источники продаж", scopes=_ORGANIZATION_ONLY),
        _capability("support.view", "Просмотр поддержки"),
        _capability("support.operate", "Работа с поддержкой"),
        _capability("notifications.manage", "Управление уведомлениями", scopes=_ORGANIZATION_ONLY),
    )
}

PROTECTED_CAPABILITIES = frozenset(
    code for code, spec in CAPABILITY_REGISTRY.items() if spec.protected
)


def capability_spec(code: str) -> CapabilitySpec:
    try:
        return CAPABILITY_REGISTRY[code]
    except KeyError as error:
        raise ValueError(f"Unknown capability: {code}") from error
