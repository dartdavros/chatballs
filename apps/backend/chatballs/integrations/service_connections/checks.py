"""Проверка доступа к сервису (SPEC-0037 R-7).

Проверка — это объявленная адаптером операция чтения (реестр не примет
другую), поэтому записей во внешней системе она не создаёт. Выполняется вне
транзакции: сетевой запрос не держит соединение с базой и блокировки.
"""

from __future__ import annotations

from typing import Any

from chatballs.integrations.adapters.contracts import AdapterDescriptor, AuthMethod, ResultState
from chatballs.integrations.adapters.schema import validate_value
from chatballs.integrations.models import Integration
from chatballs.integrations.service_connections.binding import build_context
from chatballs.integrations.service_connections.errors import ServiceCheckFailed
from chatballs.tenancy.context import TenantContext


def run_check(
    *,
    tenant: TenantContext | None,
    integration: Integration,
    adapter: AdapterDescriptor,
    method: AuthMethod,
    settings: dict[str, Any],
    credentials: dict[str, Any],
    inputs: dict[str, Any] | None = None,
) -> None:
    """Ничего не вернуть — доступ есть; иначе ``ServiceCheckFailed`` с кодом причины."""

    check = method.check
    if check is None:
        raise ServiceCheckFailed("check_unavailable")
    arguments = dict(inputs or {})
    if check.inputs is not None and validate_value(check.inputs, arguments):
        raise ServiceCheckFailed("arguments")
    operation = adapter.operation(check.operation)
    assert operation is not None  # гарантирует валидатор реестра
    context = build_context(
        tenant=tenant, integration=integration, method=method, settings=settings, credentials=credentials,
        transport_ref=adapter.transport,
    )
    result = operation.handlers.execute(context, operation, arguments)
    if result.state != ResultState.COMPLETED:
        raise ServiceCheckFailed(result.error_code or "rejected")
    problem = check.interpret(result) if check.interpret else None
    if problem:
        raise ServiceCheckFailed(problem)
