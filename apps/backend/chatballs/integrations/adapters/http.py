"""Настраиваемые HTTP/API-операции (SPEC-0037 R-5; C4 code-service-adapter-generic).

Операция описывается таблицей: метод, путь, какие аргументы идут в путь,
адрес, заголовки и тело, формат тела и где в ответе результат. Методы и тела
не урезаны до чтения; ограничения конкретного сервиса адаптер объявляет сам.

Исход определяется честно (R-20): ответ получен — успех или ошибка по
статусу; запрос мог уйти, но ответа нет — у читающей операции это ошибка, у
меняющей данные «результат неизвестен», без слепого повтора.
"""

from __future__ import annotations

import http.client
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote, urlencode, urljoin, urlsplit

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
from chatballs.integrations.adapters.forms import flatten_form, multipart_body
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.adapters.transport import TransportError, TransportResponse
from chatballs.integrations.tool_network import ToolAddressRejected

HTTP_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})
BODY_FORMATS = frozenset({"json", "form", "multipart", "none"})

# Ответ сервиса с ошибкой в теле: (статус, разобранное тело) → код или None.
Interpret = Callable[[int, Any], str | None]


@dataclass(frozen=True)
class HttpSpec:
    method: str
    path: str
    query: tuple[str, ...] = ()
    # имя аргумента → имя заголовка
    headers: dict[str, str] = field(default_factory=dict)
    body: str = "json"
    # Путь до результата в JSON-ответе через точку; пусто — весь ответ.
    result: str = ""
    # Заголовок ключа идемпотентности, если сервис его поддерживает.
    idempotency_header: str = ""
    interpret: Interpret | None = None


def http_operation(
    key: str,
    *,
    title_key: str,
    effect: Effect,
    input: TypeSpec,
    output: TypeSpec,
    spec: HttpSpec,
    retry: RetryStrategy | None = None,
    permission_scope: str = "",
    limits: Limits = DEFAULT_LIMITS,
    description_key: str = "",
    entity_kind: str = "",
) -> OperationDescriptor:
    if spec.method not in HTTP_METHODS or spec.body not in BODY_FORMATS:
        raise ValueError(f"operation {key}: unsupported method or body format")
    if retry is None:
        retry = RetryStrategy.SAFE_READ if effect in READ_EFFECTS else (
            RetryStrategy.IDEMPOTENCY_KEY if spec.idempotency_header else RetryStrategy.NONE
        )
    return OperationDescriptor(
        key=key,
        title_key=title_key,
        description_key=description_key,
        effect=effect,
        input=input,
        output=output,
        handlers=OperationHandlers(execute=execute_http),
        retry=retry,
        permission_scope=permission_scope,
        limits=limits,
        protocol={"http": spec},
        entity_kind=entity_kind,
    )


def execute_http(context: OperationContext, operation: OperationDescriptor, arguments: dict[str, Any]) -> OperationResult:
    spec: HttpSpec = operation.protocol["http"]
    try:
        request = build_http_request(context, spec, arguments)
    except (ValueError, KeyError):
        return OperationResult(ResultState.FAILED, error_code="arguments")
    request = context.auth.prepare(request, context.credentials, context.auth_options)
    try:
        response = context.transport.send(request, limits=operation.limits, store_file=context.store_file)
    except ToolAddressRejected as error:
        return OperationResult(ResultState.FAILED, error_code=f"address_{error.code}")
    except TransportError as error:
        state = ResultState.UNKNOWN if error.request_sent and operation.effect not in READ_EFFECTS else ResultState.FAILED
        return OperationResult(state, error_code=error.code)
    except (OSError, http.client.HTTPException):
        # Запрос мог дойти: меняющую операцию нельзя считать неуспешной.
        state = ResultState.FAILED if operation.effect in READ_EFFECTS else ResultState.UNKNOWN
        return OperationResult(state, error_code="no_response")
    return interpret_response(spec, response)


def build_http_request(context: OperationContext, spec: HttpSpec, arguments: dict[str, Any]) -> OutboundRequest:
    used: set[str] = set()
    path = spec.path
    for name, value in arguments.items():
        marker = f"{{{name}}}"
        if marker in path:
            text = str(value)
            if text in (".", "..") or not text:
                raise ValueError(name)
            path = path.replace(marker, quote(text, safe=""))
            used.add(name)
    base = context.auth.base_url(context.settings, context.credentials, context.auth_options)
    url = urljoin(base, path)
    if urlsplit(url).netloc != urlsplit(base).netloc:
        raise ValueError("path")
    query = [(name, _scalar(arguments[name])) for name in spec.query if arguments.get(name) is not None]
    used.update(spec.query)
    if query:
        url = f"{url}{'&' if '?' in url else '?'}{urlencode(query)}"
    headers = {"Accept": "application/json, text/*;q=0.9, */*;q=0.1"}
    for name, header in spec.headers.items():
        if arguments.get(name) is not None:
            headers[header] = _scalar(arguments[name])
        used.add(name)
    if spec.idempotency_header and context.effect_key:
        headers[spec.idempotency_header] = context.effect_key
    rest = {name: value for name, value in arguments.items() if name not in used}
    body = None
    if spec.body == "json" and spec.method not in ("GET", "HEAD"):
        headers["Content-Type"] = "application/json"
        body = json.dumps(rest, ensure_ascii=False).encode()
    elif spec.body == "form":
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = urlencode(flatten_form(rest)).encode()
    elif spec.body == "multipart":
        content_type, body = multipart_body(rest, context.open_file)
        headers["Content-Type"] = content_type
    return OutboundRequest(method=spec.method, url=url, headers=headers, body=body)


def interpret_response(spec: HttpSpec, response: TransportResponse) -> OperationResult:
    if response.file is not None:
        payload: Any = {"fileId": response.file.file_id}
    else:
        payload = _parsed(response)
    vendor_error = spec.interpret(response.status, payload) if spec.interpret else None
    if vendor_error is None and 200 <= response.status < 300:
        return OperationResult(
            ResultState.COMPLETED,
            data=_dig(payload, spec.result),
            files=(response.file,) if response.file else (),
        )
    retry_after = _retry_after(response.headers.get("retry-after", ""))
    return OperationResult(
        ResultState.FAILED,
        error_code=vendor_error or _status_code(response.status),
        retry_after_seconds=retry_after,
    )


def _status_code(status: int) -> str:
    if status == 401:
        return "unauthorized"
    if status == 403:
        return "forbidden"
    if status == 404:
        return "not_found"
    if status == 429:
        return "rate_limited"
    if status >= 500:
        return "temporary"
    return "rejected"


def _parsed(response: TransportResponse) -> Any:
    if response.content_type.endswith("json"):
        try:
            return json.loads(response.body or b"null")
        except ValueError:
            return None
    return response.body.decode("utf-8", "replace")


def _dig(payload: Any, path: str) -> Any:
    for part in [item for item in path.split(".") if item]:
        payload = payload.get(part) if isinstance(payload, dict) else None
    return payload


def _retry_after(value: str) -> float | None:
    if value.strip().isdigit():
        try:
            delay = float(value)
            return delay if delay <= 315360000 else None
        except (ValueError, OverflowError):
            return None
    try:
        when = parsedate_to_datetime(value)
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        return max(0, (when - datetime.now(UTC)).total_seconds())
    except (ValueError, TypeError, OverflowError):
        return None


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
