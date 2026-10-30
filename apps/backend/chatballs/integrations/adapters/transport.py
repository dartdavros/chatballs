"""Защищённый транспорт адаптеров (SPEC-0037 R-4, R-7; C4 code-service-adapter-network).

Тот же контур, что у инструментов агента (``tool_network``/``tool_client``):
адрес проверяется после DNS, соединение идёт на проверенный IP, каждое
перенаправление проверяется заново, а авторизация не уходит на чужой origin.
Частные сети открывает только настройка администратора установки.

В отличие от инструментов, метод и тело не ограничены чтением, а ответ не
обязан быть текстом: большой или бинарный ответ уходит в штатное файловое
хранилище, дальше ходит ссылка на файл.
"""

from __future__ import annotations

import os
import ssl
import tempfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from typing import IO
from urllib.parse import urljoin

from chatballs.integrations.adapters.auth import OutboundRequest
from chatballs.integrations.adapters.contracts import FileRef, Limits
from chatballs.integrations.adapters.registry import Extension
from chatballs.integrations.proxy import user_agent
from chatballs.integrations.tool_client import (
    ORIGIN_NEUTRAL_HEADERS,
    REDIRECT_STATUSES,
    origin_of,
    pinned_connection,
    remaining_time,
)
from chatballs.integrations.tool_network import check_tool_url

MAX_REDIRECTS = 3
_CHUNK_BYTES = 64 * 1024

# Сохраняет поток ответа в хранилище организации: (имя, тип, поток, размер).
StoreFile = Callable[[str, str, IO[bytes], int], FileRef]


class TransportError(Exception):
    """Ответ не получен или не принят; ``code`` — причина без данных сервиса."""

    def __init__(self, code: str, *, request_sent: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.request_sent = request_sent


@dataclass(frozen=True)
class TransportResponse:
    status: int
    content_type: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    file: FileRef | None = None


class GuardedTransport:
    def send(self, request: OutboundRequest, *, limits: Limits, store_file: StoreFile | None = None) -> TransportResponse:
        from chatballs.identity.instance_settings import tools_private_network_allowed

        allow_private = tools_private_network_allowed()
        deadline: float | None = None
        with _client_context(request.client_certificate) as context:
            for _ in range(MAX_REDIRECTS + 1):
                target = check_tool_url(request.url, allow_private=allow_private)
                # Срок — на разговор с сервисом: проверка адреса по политике
                # установки его не расходует.
                deadline = deadline or time.monotonic() + limits.timeout_seconds
                connection = _connected(target, deadline, context)
                try:
                    # С этого места запрос мог дойти: сбой дальше — не «не отправлено».
                    connection.request(
                        request.method,
                        target.request_target,
                        body=request.body,
                        headers={"User-Agent": user_agent(), **request.headers},
                    )
                    response = connection.getresponse()
                    location = response.headers.get("Location") if response.status in REDIRECT_STATUSES else None
                    if not location:
                        return _accept(response, connection, deadline, request.url, limits, store_file)
                    status = response.status
                except TransportError as error:
                    error.request_sent = True
                    raise
                finally:
                    connection.close()
                try:
                    request = _redirected(request, status, urljoin(request.url, location))
                except TransportError as error:
                    error.request_sent = True
                    raise
        raise TransportError("too_many_redirects", request_sent=True)


def _connected(target, deadline: float, context):
    """Соединение до отправки запроса: его сбой точно означает, что запроса не было."""

    try:
        connection = pinned_connection(target, remaining_time(deadline), context)
        connection.connect()
    except OSError as error:
        raise TransportError("unreachable") from error
    return connection


def _redirected(request: OutboundRequest, status: int, next_url: str) -> OutboundRequest:
    headers = request.headers
    if origin_of(next_url) != origin_of(request.url):
        # TLS передаёт сертификат до HTTP-заголовков; одной очистки headers
        # недостаточно, чтобы не раскрыть доступ постороннему серверу.
        if request.client_certificate:
            raise TransportError("address_forbidden")
        headers = {name: value for name, value in headers.items() if name.lower() in ORIGIN_NEUTRAL_HEADERS}
    method, body = request.method, request.body
    if status == 303 or (status in (301, 302) and method != "GET"):
        method, body = "GET", None
        headers = {name: value for name, value in headers.items() if name.lower() != "content-type"}
    return replace(request, url=next_url, method=method, body=body, headers=headers)


def _accept(response, connection, deadline, url, limits: Limits, store_file: StoreFile | None) -> TransportResponse:
    content_type = response.headers.get_content_type() if response.headers.get("Content-Type") else ""
    headers = {name.lower(): value for name, value in response.headers.items()}
    declared = response.headers.get("Content-Length", "")
    size_hint = int(declared) if declared.isdigit() else None
    inline = _is_text(content_type) and (size_hint is None or size_hint <= limits.max_response_bytes)
    if size_hint is not None and size_hint > limits.max_file_bytes:
        raise TransportError("too_large")
    with tempfile.SpooledTemporaryFile(max_size=limits.max_response_bytes) as buffer:
        size = 0
        while True:
            connection.pinned_sock.settimeout(remaining_time(deadline))
            chunk = response.read1(_CHUNK_BYTES)
            if not chunk:
                break
            size += len(chunk)
            if size > limits.max_file_bytes:
                raise TransportError("too_large")
            buffer.write(chunk)
        buffer.seek(0)
        if inline and size <= limits.max_response_bytes:
            return TransportResponse(response.status, content_type, url, headers, body=buffer.read())
        if store_file is None:
            raise TransportError("too_large")
        name = os.path.basename(url.split("?", 1)[0]) or "response"
        stored = store_file(name, content_type or "application/octet-stream", buffer, size)
        return TransportResponse(response.status, content_type, url, headers, file=stored)


def _is_text(content_type: str) -> bool:
    return not content_type or content_type in ("application/json", "application/problem+json") or content_type.startswith("text/")


@contextmanager
def _client_context(pair: tuple[str, str] | None) -> Iterator[ssl.SSLContext | None]:
    """TLS-контекст с сертификатом клиента; PEM лежит на диске только миг загрузки."""

    if not pair:
        yield None
        return
    context = ssl.create_default_context()
    paths: list[str] = []
    try:
        for pem in pair:
            handle, path = tempfile.mkstemp(suffix=".pem")
            paths.append(path)
            with os.fdopen(handle, "w") as stream:
                stream.write(pem)
        context.load_cert_chain(certfile=paths[0], keyfile=paths[1])
    except (ssl.SSLError, OSError) as error:
        raise TransportError("certificate") from error
    finally:
        for path in paths:
            os.unlink(path)
    yield context


def builtin_extensions() -> list[Extension]:
    return [Extension("transport", "https", 1, GuardedTransport())]
