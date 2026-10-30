"""Совместимый мост к существующим HTTP/MCP-серверам (SPEC-0037 R-5, R-29).

Внешний сервер остаётся своим ``Integration``: мост описывает его операции
общим контрактом и при вызове читает адрес и секретные заголовки из исходной
записи. Секреты не копируются, переподключение не нужно.

Мост ничего не разрешает: инструменты агентов (``AgentTool``) и подтверждения
«только читает» не меняются, а запись помечается записью — без ложной
отметки «только чтение». Вызвать её новый контур сможет лишь после явного
разрешения, которое выдают последующие части механизма.
"""

from __future__ import annotations

import http.client
from dataclasses import replace
from typing import Any

from chatballs.integrations import http_tool, mcp_client
from chatballs.integrations.adapters.contracts import (
    READ_EFFECTS,
    AdapterDescriptor,
    Effect,
    OperationContext,
    OperationDescriptor,
    OperationHandlers,
    OperationResult,
    Presentation,
    ResultState,
    RetryStrategy,
)
from chatballs.integrations.adapters.mcp import operations_from_tools, parse_text_result
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.external_check import check_timeout
from chatballs.integrations.external_tools import call_tool
from chatballs.integrations.models import Integration, IntegrationProvider
from chatballs.integrations.read_only import server_tools
from chatballs.integrations.tool_client import ToolResponseRejected
from chatballs.integrations.tool_network import ToolAddressRejected

LEGACY_KEYS = {IntegrationProvider.MCP: "legacy_mcp", IntegrationProvider.HTTP: "legacy_http"}
_METHOD_EFFECT = {"GET": Effect.READ, "POST": Effect.CREATE, "PUT": Effect.UPDATE, "PATCH": Effect.UPDATE, "DELETE": Effect.DELETE}
_PRESENTATION = Presentation(
    title_key="services.legacy_title",
    about_key="services.legacy_about",
    connect_lead_key="",
    logo_light="",
    logo_dark="",
    host_label_key="services.host_address",
)


def is_bridged(integration: Integration) -> bool:
    return integration.provider in LEGACY_KEYS


def bridge_descriptor(integration: Integration) -> AdapterDescriptor:
    """Описание операций внешнего сервера по его сохранённой конфигурации."""

    if integration.provider == IntegrationProvider.MCP:
        operations = _mcp_operations(integration)
    elif integration.provider == IntegrationProvider.HTTP:
        operations = (_http_operation(integration),)
    else:
        raise ValueError("not an external server")
    return AdapterDescriptor(
        key=LEGACY_KEYS[integration.provider],
        contract_version=1,
        presentation=_PRESENTATION,
        auth_methods=(),
        operations=operations,
        listed=False,
    )


def _mcp_operations(integration: Integration) -> tuple[OperationDescriptor, ...]:
    read_only = {tool.name for tool in server_tools(integration) if tool.read_only}
    operations = operations_from_tools(integration.tools, read_only=read_only)
    # Вызов идёт через сохранённый сервер со своими заголовками.
    return tuple(_with_execute(operation, _execute_legacy_mcp) for operation in operations)


def _http_operation(integration: Integration) -> OperationDescriptor:
    config = integration.config
    method = str(config.get("method", "GET")).upper()
    read_only = server_tools(integration)[0].read_only
    effect = Effect.READ if read_only else _METHOD_EFFECT.get(method, Effect.OTHER)
    return OperationDescriptor(
        key="request",
        title_key="",
        effect=effect,
        input=_http_input(config),
        output=TypeSpec("object", open=True, nullable=True),
        handlers=OperationHandlers(execute=_execute_legacy_http),
        retry=RetryStrategy.SAFE_READ if effect in READ_EFFECTS else RetryStrategy.NONE,
        protocol={"legacy": {"method": method}},
    )


def _http_input(config: dict[str, Any]) -> TypeSpec:
    kinds = {"string": "string", "number": "number", "integer": "integer", "boolean": "boolean"}
    properties = tuple(
        (str(parameter["name"]), TypeSpec(kinds.get(parameter.get("type"), "string"), required=bool(parameter.get("required"))))
        for parameter in config.get("parameters") or []
        if isinstance(parameter, dict) and parameter.get("name")
    )
    return TypeSpec("object", properties=properties)


def _with_execute(operation: OperationDescriptor, execute) -> OperationDescriptor:
    return replace(operation, handlers=OperationHandlers(execute=execute))


def _execute_legacy_mcp(context: OperationContext, operation: OperationDescriptor, arguments: dict[str, Any]) -> OperationResult:
    try:
        result = call_tool(context.connection, operation.protocol["mcp"]["tool"], arguments, timeout=check_timeout())
    except mcp_client.McpError as error:
        state = ResultState.FAILED if operation.effect in READ_EFFECTS else ResultState.UNKNOWN
        return OperationResult(state, error_code=error.code)
    if result.is_error:
        return OperationResult(ResultState.FAILED, error_code="tool_error")
    return OperationResult(ResultState.COMPLETED, data=parse_text_result(result.text))


def _execute_legacy_http(context: OperationContext, operation: OperationDescriptor, arguments: dict[str, Any]) -> OperationResult:
    config = context.connection.config
    bound_names = {
        parameter["name"]
        for parameter in config.get("parameters") or []
        if isinstance(parameter, dict) and parameter.get("source", {}).get("type") != "ai"
    }
    model = {name: value for name, value in arguments.items() if name not in bound_names}
    bound = {name: value for name, value in arguments.items() if name in bound_names}
    try:
        response = http_tool.call_http_tool(context.connection, model, bound, timeout=check_timeout())
    except http_tool.ToolArgumentsRejected:
        return OperationResult(ResultState.FAILED, error_code="arguments")
    except ToolAddressRejected as error:
        return OperationResult(ResultState.FAILED, error_code=f"address_{error.code}")
    except ToolResponseRejected as error:
        return OperationResult(ResultState.FAILED, error_code=error.code)
    except (OSError, http.client.HTTPException):
        state = ResultState.FAILED if operation.effect in READ_EFFECTS else ResultState.UNKNOWN
        return OperationResult(state, error_code="no_response")
    if 200 <= response.status < 300:
        return OperationResult(ResultState.COMPLETED, data=parse_text_result(response.body.decode("utf-8", "replace")))
    return OperationResult(ResultState.FAILED, error_code="rejected")
