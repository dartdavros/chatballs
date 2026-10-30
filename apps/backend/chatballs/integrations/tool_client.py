"""Исходящий клиент инструментов агента: один на MCP и HTTP-запросы.

От общего opener (``integrations.proxy``) он отличается тем, что соединяется
не с именем, а с IP, который прошёл проверку (``tool_network``): между
проверкой и соединением имя второй раз не разрешается, и DNS rebinding не
подменит адрес. По перенаправлениям клиент ходит сам — не больше трёх, каждое
проверяется так же, как исходный адрес (SPEC-0023 R-16).

Ответ принимается только ``application/json`` или ``text/*`` и не больше
256 КБ (R-18). Срок задаёт вызывающий, и он один на весь запрос вместе с
перенаправлениями и чтением тела.
"""

from __future__ import annotations

import http.client
import socket
import ssl
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

from chatballs.integrations.proxy import user_agent
from chatballs.integrations.tool_network import ToolTarget, check_tool_url

MAX_RESPONSE_BYTES = 256 * 1024
MAX_REDIRECTS = 3

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_READ_CHUNK_BYTES = 64 * 1024
# Что переживает перенаправление на другой хост: заголовки авторизации
# администратор выдал одному серверу, и чужому они не предназначены.
_ORIGIN_NEUTRAL_HEADERS = frozenset({"accept", "content-type"})


class ToolResponseRejected(Exception):
    """Ответ не принят; ``code`` — причина без текста чужого сервера."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ToolResponse:
    status: int
    content_type: str
    body: bytes
    url: str
    # Имена в нижнем регистре.
    headers: dict[str, str] = field(default_factory=dict)


def fetch(
    url: str,
    *,
    timeout: float,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> ToolResponse:
    """Выполнить запрос инструмента.

    Отказ адреса — ``ToolAddressRejected``, отказ ответа —
    ``ToolResponseRejected``; сетевые ошибки и истёкший срок (``OSError``,
    ``http.client.HTTPException``) уходят вызывающему как есть.
    """
    from chatballs.identity.instance_settings import tools_private_network_allowed

    allow_private = tools_private_network_allowed()
    deadline = time.monotonic() + timeout
    headers = dict(headers or {})
    for _ in range(MAX_REDIRECTS + 1):
        target = check_tool_url(url, allow_private=allow_private)
        connection = _connection(target, _remaining(deadline))
        try:
            connection.request(
                method, target.request_target, body=body, headers={"User-Agent": user_agent(), **headers}
            )
            response = connection.getresponse()
            location = response.headers.get("Location") if response.status in _REDIRECT_STATUSES else None
            if not location:
                return _accept(response, connection, deadline, url)
            status = response.status
        finally:
            connection.close()
        next_url = urljoin(url, location)
        if _origin(next_url) != _origin(url):
            headers = {k: v for k, v in headers.items() if k.lower() in _ORIGIN_NEUTRAL_HEADERS}
        if status == 303 or (status in (301, 302) and method != "GET"):
            method, body = "GET", None
            headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}
        url = next_url
    raise ToolResponseRejected("too_many_redirects")


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError:
        port = None
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), port


def _remaining(deadline: float) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError("tool request deadline exceeded")
    return left


def _accept(response, connection, deadline: float, url: str) -> ToolResponse:
    has_type = bool(response.headers.get("Content-Type"))
    content_type = response.headers.get_content_type() if has_type else ""
    # Тип проверяется до чтения: чужой файл незачем и скачивать.
    if has_type and not _is_text(content_type):
        raise ToolResponseRejected("content_type")
    declared = response.headers.get("Content-Length", "")
    if declared.isdigit() and int(declared) > MAX_RESPONSE_BYTES:
        raise ToolResponseRejected("too_large")
    chunks: list[bytes] = []
    size = 0
    while True:
        # Срок общий: сервер, отдающий по байту, не растянет запрос сверх него.
        connection.pinned_sock.settimeout(_remaining(deadline))
        chunk = response.read1(_READ_CHUNK_BYTES)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise ToolResponseRejected("too_large")
        chunks.append(chunk)
    # Пустой ответ без типа — обычное дело (202 на уведомление MCP).
    if size and not has_type:
        raise ToolResponseRejected("content_type")
    return ToolResponse(
        status=response.status,
        content_type=content_type,
        body=b"".join(chunks),
        url=url,
        headers={name.lower(): value for name, value in response.headers.items()},
    )


def _is_text(content_type: str) -> bool:
    return content_type == "application/json" or content_type.startswith("text/")


def _open_socket(address: str, port: int, timeout: float) -> socket.socket:
    return socket.create_connection((address, port), timeout)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """Соединение с проверенным IP; Host остаётся именем из адреса."""

    def __init__(self, target: ToolTarget, timeout: float, ssl_context: ssl.SSLContext | None = None) -> None:
        super().__init__(target.host, target.port, timeout=timeout)
        self._address = target.address
        self._ssl_context = ssl_context
        self.pinned_sock: socket.socket | None = None

    def connect(self) -> None:
        self.sock = self.pinned_sock = _open_socket(self._address, self.port, self.timeout)


class _PinnedHTTPSConnection(_PinnedHTTPConnection):
    """То же по TLS: сертификат сверяется с именем хоста, а не с IP."""

    default_port = http.client.HTTPS_PORT

    def connect(self) -> None:
        raw = _open_socket(self._address, self.port, self.timeout)
        context = self._ssl_context or ssl.create_default_context()
        self.sock = self.pinned_sock = context.wrap_socket(raw, server_hostname=self.host)


def _connection(target: ToolTarget, timeout: float, ssl_context: ssl.SSLContext | None = None) -> _PinnedHTTPConnection:
    factory = _PinnedHTTPSConnection if target.scheme == "https" else _PinnedHTTPConnection
    return factory(target, timeout, ssl_context)


# Сервисные адаптеры (adapters/transport.py) ходят тем же закреплённым
# соединением и по тем же правилам перенаправлений.
pinned_connection = _connection
origin_of = _origin
remaining_time = _remaining
ORIGIN_NEUTRAL_HEADERS = _ORIGIN_NEUTRAL_HEADERS
REDIRECT_STATUSES = _REDIRECT_STATUSES
