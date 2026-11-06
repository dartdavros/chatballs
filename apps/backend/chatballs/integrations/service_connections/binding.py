"""Связь подключения с адаптером: серверный контекст операции (SPEC-0037 R-7, R-14).

Контекст собирает только сервер: организация и подключение — из tenant-
контекста, способ доступа — из сохранённых настроек, credentials
расшифровываются на время вызова и в контекст попадают лишь в памяти.
Входные данные операции проверяются по её схеме до любого запроса.
"""

from __future__ import annotations

import json
from typing import Any

from chatballs.integrations.adapters.contracts import (
    AdapterDescriptor,
    AuthMethod,
    LookupItem,
    OperationContext,
    OperationResult,
    ResultState,
)
from chatballs.integrations.adapters.files import file_store
from chatballs.integrations.adapters.registry import AdapterRegistry, default_registry
from chatballs.integrations.adapters.schema import validate_value
from chatballs.integrations.models import Integration, ServiceConnectionSettings
from chatballs.tenancy.context import TenantContext


class ServiceUnavailable(Exception):
    """Подключение нельзя использовать; ``code`` — причина без подробностей."""

    def __init__(self, code: str, *, adapter: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.adapter = adapter


def load_credentials(row: ServiceConnectionSettings) -> dict[str, Any]:
    try:
        value = json.loads(row.credentials or "{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def dump_credentials(values: dict[str, Any]) -> str:
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def resolve(integration: Integration, registry: AdapterRegistry | None = None) -> tuple[ServiceConnectionSettings, AdapterDescriptor, AuthMethod]:
    registry = registry or default_registry()
    row = integration.service_settings
    adapter = registry.adapter(row.adapter_key)
    if adapter is None:
        raise ServiceUnavailable("adapter_unknown")
    if row.adapter_version != adapter.contract_version:
        # Новая версия пакета не переинтерпретирует старое подключение молча.
        raise ServiceUnavailable("version_incompatible")
    method = adapter.auth_method(row.auth_method)
    if method is None:
        raise ServiceUnavailable("auth_method_unknown")
    return row, adapter, method


def build_context(
    *,
    tenant: TenantContext | None,
    integration: Integration,
    method: AuthMethod,
    settings: dict[str, Any],
    credentials: dict[str, Any],
    registry: AdapterRegistry | None = None,
    effect_key: str = "",
    transport_ref: str = "https@1",
) -> OperationContext:
    registry = registry or default_registry()
    auth = registry.extension("auth", method.extension)
    transport = registry.extension("transport", transport_ref)
    saved = integration.pk is not None and tenant is not None
    return OperationContext(
        organization_id=integration.organization_id,
        connection=integration,
        settings=settings,
        credentials=credentials,
        effect_key=effect_key,
        auth=auth.implementation,
        auth_options=method.options,
        transport=transport.implementation,
        # Проверка ещё не сохранённого подключения файлов не создаёт.
        store_file=file_store(context=tenant, integration=integration) if saved else None,
        open_file=_file_opener(integration.organization_id) if saved else None,
    )


def execute(
    *,
    tenant: TenantContext,
    integration: Integration,
    operation_key: str,
    arguments: dict[str, Any],
    effect_key: str = "",
    registry: AdapterRegistry | None = None,
) -> OperationResult:
    """Выполнить операцию сохранённого подключения (общий вход исполнителя)."""

    if integration.organization_id != tenant.organization_id:
        raise ServiceUnavailable("not_found")
    if not integration.is_active:
        raise ServiceUnavailable("paused")
    row, adapter, method = resolve(integration, registry)
    operation = adapter.operation(operation_key)
    if operation is None:
        raise ServiceUnavailable("operation_unknown")
    if validate_value(operation.input, arguments):
        return OperationResult(ResultState.FAILED, error_code="arguments")
    from chatballs.integrations.service_connections.errors import ServiceCheckFailed
    from chatballs.integrations.service_connections.oauth import fresh_credentials

    try:
        credentials = fresh_credentials(tenant=tenant, integration=integration, row=row, method=method)
    except ServiceCheckFailed as error:
        return OperationResult(ResultState.FAILED, error_code=error.code)
    context = build_context(
        tenant=tenant, integration=integration, method=method, settings=row.settings,
        credentials=credentials, registry=registry, effect_key=effect_key, transport_ref=adapter.transport,
    )
    return operation.handlers.execute(context, operation, arguments)


def load_lookup(*, tenant: TenantContext, integration: Integration, key: str) -> list[LookupItem]:
    _row, adapter, _method = resolve(integration)
    lookup = adapter.lookup(key)
    if lookup is None:
        raise ServiceUnavailable("lookup_unknown")
    result = execute(tenant=tenant, integration=integration, operation_key=lookup.operation, arguments=lookup.arguments)
    if result.state != ResultState.COMPLETED:
        raise ServiceUnavailable(result.error_code or "rejected", adapter=adapter.key)
    return lookup.items(result.data)


def _file_opener(organization_id: int):
    from chatballs.integrations.adapters.file_access import file_opener
    return file_opener(organization_id)
