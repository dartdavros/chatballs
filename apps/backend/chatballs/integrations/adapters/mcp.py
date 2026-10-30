"""MCP-операции (SPEC-0037 R-5; C4 code-service-adapter-generic).

Операция — инструмент, объявленный сервером. Эффект берётся из его отметок:
``readOnlyHint`` — чтение, ``destructiveHint`` — удаление, иначе — изменение
без уточнения. Запись не запрещена: что разрешено вызывать, решают права
нового контура, а не этот исполнитель.
"""

from __future__ import annotations

import json
import re
from typing import Any

from chatballs.integrations import mcp_client
from chatballs.integrations.adapters.auth import OutboundRequest
from chatballs.integrations.adapters.contracts import (
    DEFAULT_LIMITS,
    READ_EFFECTS,
    Effect,
    Limits,
    OperationContext,
    OperationDescriptor,
    OperationHandlers,
    OperationResult,
    ResultState,
    RetryStrategy,
)
from chatballs.integrations.adapters.json_schema import typespec_from_json_schema
from chatballs.integrations.adapters.schema import TypeSpec

# Причины, при которых запрос к инструменту точно не выполнен.
_NOT_SENT = frozenset({mcp_client.ADDRESS_FORBIDDEN, mcp_client.UNAUTHORIZED, mcp_client.REJECTED})
_ANY = TypeSpec("object", open=True, nullable=True)


def mcp_operation(
    key: str,
    *,
    tool: str,
    title_key: str,
    effect: Effect,
    input: TypeSpec,
    output: TypeSpec = _ANY,
    permission_scope: str = "",
    limits: Limits = DEFAULT_LIMITS,
    description_key: str = "",
) -> OperationDescriptor:
    return OperationDescriptor(
        key=key,
        title_key=title_key,
        description_key=description_key,
        effect=effect,
        input=input,
        output=output,
        handlers=OperationHandlers(execute=execute_mcp),
        retry=RetryStrategy.SAFE_READ if effect in READ_EFFECTS else RetryStrategy.NONE,
        permission_scope=permission_scope,
        limits=limits,
        protocol={"mcp": {"tool": tool}},
    )


def effect_of(tool: dict[str, Any], *, read_only: bool) -> Effect:
    if read_only:
        return Effect.READ
    annotations = tool.get("annotations") if isinstance(tool.get("annotations"), dict) else {}
    if annotations.get("destructiveHint") is True:
        return Effect.DELETE
    return Effect.OTHER


def operations_from_tools(tools: list[dict[str, Any]], *, read_only: set[str]) -> tuple[OperationDescriptor, ...]:
    """Операции по снимку ``tools/list``; ключ операции выводится из имени инструмента."""

    taken: set[str] = set()
    operations = []
    for tool in tools:
        key = operation_key(str(tool["name"]), taken)
        taken.add(key)
        operations.append(
            mcp_operation(
                key,
                tool=str(tool["name"]),
                title_key="",
                effect=effect_of(tool, read_only=tool["name"] in read_only),
                input=typespec_from_json_schema(tool.get("input_schema") or tool.get("inputSchema")),
            )
        )
    return tuple(operations)


def operation_key(name: str, taken: set[str]) -> str:
    """Стабильный ключ операции из имени инструмента (имена MCP свободнее ключей)."""

    base = "tool." + (re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_") or "unnamed")
    base = re.sub(r"\.(?=[0-9_])", ".t_", base)
    key, suffix = base, 2
    while key in taken:
        key, suffix = f"{base}_{suffix}", suffix + 1
    return key


def execute_mcp(context: OperationContext, operation: OperationDescriptor, arguments: dict[str, Any]) -> OperationResult:
    url = context.auth.base_url(context.settings, context.credentials, context.auth_options)
    prepared = context.auth.prepare(OutboundRequest("POST", url), context.credentials, context.auth_options)
    try:
        result = mcp_client.call_tool(
            prepared.url,
            operation.protocol["mcp"]["tool"],
            arguments,
            headers=prepared.headers,
            timeout=operation.limits.timeout_seconds,
        )
    except mcp_client.McpError as error:
        sent = error.code not in _NOT_SENT
        state = ResultState.UNKNOWN if sent and operation.effect not in READ_EFFECTS else ResultState.FAILED
        return OperationResult(state, error_code=error.code)
    if result.is_error:
        return OperationResult(ResultState.FAILED, error_code="tool_error")
    return OperationResult(ResultState.COMPLETED, data=parse_text_result(result.text))


def parse_text_result(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        return text
