"""Один вызов инструмента в ходе агента (SPEC-0023 R-12, R-13).

Аргументы модели приходят с токенами — сервер раскрывает их по карте хода и
добавляет привязанные параметры. Результат уходит модели под маской той же
карты. Любая неудача — код ошибки вместо результата: ни тела чужого ответа,
ни текста исключения модель не получает, а ход продолжается.
"""

from __future__ import annotations

import http.client
import json
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field

from chatballs.ai.provider.base import ToolCall
from chatballs.ai.pseudonymization import Pseudonymizer
from chatballs.ai.tool_result import masked_result
from chatballs.ai.turn_tools import TurnTool
from chatballs.integrations.external_tools import call_tool
from chatballs.integrations.http_tool import ToolArgumentsRejected, call_http_tool
from chatballs.integrations.mcp_client import (
    ADDRESS_FORBIDDEN,
    BAD_RESPONSE,
    TIMEOUT,
    UNAUTHORIZED,
    UNREACHABLE,
    McpError,
)
from chatballs.integrations.models import IntegrationProvider
from chatballs.integrations.tool_client import ToolResponseRejected
from chatballs.integrations.tool_network import ToolAddressRejected

logger = logging.getLogger(__name__)

TOOL_TIMEOUT_SECONDS = 30.0

NOT_FOUND = "not_found"
INVALID_ARGUMENTS = "invalid_arguments"
UNKNOWN_TOOL = "unknown_tool"
# Инструмент MCP отработал, но сообщил об ошибке (``isError``).
TOOL_ERROR = "tool_error"


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    """След вызова для оператора: без аргументов и без ответа (R-19)."""

    name: str
    title: str
    # Код ошибки; пусто — вызов удался.
    error: str
    duration_ms: int
    diagnostic: dict = field(default_factory=dict, repr=False, compare=False)


class _Failed(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _payload(**fields: str) -> str:
    return json.dumps(fields, separators=(",", ":"))


def _revealed(value: object, pseudonymizer: Pseudonymizer) -> object:
    """Аргументы с настоящими значениями вместо токенов хода."""
    if isinstance(value, str):
        return pseudonymizer.restore(value).text
    if isinstance(value, dict):
        return {key: _revealed(item, pseudonymizer) for key, item in value.items()}
    if isinstance(value, list):
        return [_revealed(item, pseudonymizer) for item in value]
    return value


def _call_http(tool: TurnTool, arguments: dict, timeout: float, diagnostic: dict) -> str:
    try:
        response = call_http_tool(tool.integration, arguments, tool.bound, timeout=timeout)
    except ToolArgumentsRejected as error:
        raise _Failed(INVALID_ARGUMENTS) from error
    except ToolAddressRejected as error:
        code = UNREACHABLE if error.code == "unresolved" else ADDRESS_FORBIDDEN
        raise _Failed(code) from error
    except ToolResponseRejected as error:
        raise _Failed(BAD_RESPONSE) from error
    except TimeoutError as error:
        raise _Failed(TIMEOUT) from error
    except (OSError, http.client.HTTPException, ValueError) as error:
        raise _Failed(UNREACHABLE) from error
    diagnostic["httpStatus"] = response.status
    if response.status in (401, 403):
        raise _Failed(UNAUTHORIZED)
    if response.status == 404:
        raise _Failed(NOT_FOUND)
    if response.status >= 400:
        raise _Failed(BAD_RESPONSE)
    return response.body.decode("utf-8", errors="replace")


def _call_mcp(tool: TurnTool, arguments: dict, timeout: float) -> str:
    try:
        result = call_tool(tool.integration, tool.spec.name, arguments, timeout=timeout)
    except McpError as error:
        raise _Failed(error.code) from error
    if result.is_error:
        raise _Failed(TOOL_ERROR)
    return result.text


def execute_tool_call(
    call: ToolCall,
    tools: Mapping[str, TurnTool],
    pseudonymizer: Pseudonymizer,
    *,
    time_left: float | None = None,
) -> tuple[str, ToolCallRecord]:
    """Шаг без транзакции: вызвать инструмент; вернуть текст для модели и след вызова.

    ``time_left`` — сколько осталось до срока хода: вызов ждёт не дольше него
    и не дольше 30 секунд.
    """
    started = time.monotonic()
    tool = tools.get(call.name)
    timeout = TOOL_TIMEOUT_SECONDS if time_left is None else min(time_left, TOOL_TIMEOUT_SECONDS)
    error = ""
    diagnostic = {"callId": call.id, "arguments": call.arguments}
    try:
        if tool is None:
            raise _Failed(UNKNOWN_TOOL)
        if timeout <= 0:
            raise _Failed(TIMEOUT)
        arguments = _revealed(call.arguments, pseudonymizer)
        is_http = tool.integration.provider == IntegrationProvider.HTTP
        text = (_call_http(tool, arguments, timeout, diagnostic) if is_http
                else _call_mcp(tool, arguments, timeout))
        content = masked_result(text, pseudonymizer) or _payload(result="")
    except _Failed as failure:
        error = failure.code
    except Exception as failure:  # noqa: BLE001 - сбой инструмента ход не роняет
        # Только тип: в тексте исключения может оказаться кусок чужого ответа.
        logger.warning("Tool call failed unexpectedly: %s", type(failure).__name__)
        error = BAD_RESPONSE
    if error:
        content = _payload(error=error)
    record = ToolCallRecord(
        name=call.name[:128],
        title=tool.title if tool is not None else call.name[:128],
        error=error,
        duration_ms=int((time.monotonic() - started) * 1000),
        diagnostic={**diagnostic, "modelResult": content},
    )
    return content, record
