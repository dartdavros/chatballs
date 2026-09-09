"""Shared transport primitives (M2): normalized inbound message + HTTP with
optional per-connection proxy (config["proxy_url"], e.g. http://host:port или
socks5://host:port). HTTP/HTTPS/SOCKS5 — единый opener в integrations.proxy."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field

from django.conf import settings

from chatballs.integrations.outbound import ensure_downloadable
from chatballs.integrations.proxy import build_opener

MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024


@dataclass(frozen=True)
class InboundFile:
    """Файл/фото во входящем сообщении: у провайдера (file_id или url) либо
    телом запроса (web-виджет, письмо)."""

    name: str = ""
    content_type: str = ""
    size: int = 0
    file_id: str = ""
    url: str = ""
    content: bytes = b""
    # Фото (превью в ленте) vs документ.
    is_image: bool = False


@dataclass(frozen=True)
class InboundMessage:
    external_id: str
    user_id: str
    chat_id: str
    text: str
    display_name: str
    # Публичный логин отправителя (@username), если задан.
    username: str = ""
    # Телефон из явного шаринга контакта (кнопка/форма); text при этом может быть пуст.
    phone: str = ""
    # Внешний URL аватара отправителя, если провайдер отдаёт его в профиле
    # (например, MAX присылает avatar_url). Telegram фото в getUpdates не отдаёт.
    avatar_url: str = ""
    # Безопасный форматированный вариант входящего письма. Plain text остаётся
    # обязательным fallback для AI, поиска, уведомлений и превью.
    content_html: str = ""
    # Транспортная мета для тредирования ответа (email: subject/last_message_id).
    # Пишется в Conversation.transport_meta при ingest (ADR-CHATBALLS-0035).
    thread_meta: dict | None = None
    # Голосовое сообщение (дизайн-базлайн v2, кадр H): идентификатор файла у
    # провайдера (TG file_id) ИЛИ прямой URL (MAX), длительность и mime.
    voice_file_id: str = ""
    voice_url: str = ""
    # Голосовое, пришедшее телом запроса (web-виджет): скачивать нечего.
    voice_content: bytes = b""
    voice_duration: int = 0
    voice_mime: str = ""
    # Файлы и фото: каждый становится отдельным сообщением kind=file.
    files: tuple[InboundFile, ...] = field(default_factory=tuple)


def request_json(url: str, *, headers: dict | None = None, method: str = "GET", body: dict | None = None, proxy_url: str = "") -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with build_opener(proxy_url).open(request, timeout=settings.CHATBALLS_AI_REQUEST_TIMEOUT) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def first(d: dict, *keys, default=None):
    for key in keys:
        value = d.get(key)
        if value not in (None, ""):
            return value
    return default


def download_bytes(
    url: str,
    *,
    proxy_url: str = "",
    max_bytes: int = MAX_ATTACHMENT_BYTES,
    allowed_host: str = "",
) -> bytes:
    """Скачивание файла провайдера (голосовые ~десятки КБ; жёсткий предел 20МБ).

    Адрес приходит ответом провайдера, то есть данными, а не настройкой: его
    проверяет политика исходящих запросов (``integrations.outbound``).
    ``allowed_host`` — хост из ``base_url`` подключения, который владелец
    назвал сам.
    """
    def guard(candidate: str) -> None:
        ensure_downloadable(candidate, allowed_host=allowed_host, via_proxy=bool(proxy_url))

    guard(url)
    request = urllib.request.Request(url)
    # Та же проверка на каждый редирект: провайдер отдаёт адрес данными, и
    # 302 увёл бы скачивание туда, куда исходный адрес не пустили.
    opener = build_opener(proxy_url, validate_redirect=guard)
    with opener.open(request, timeout=settings.CHATBALLS_AI_REQUEST_TIMEOUT) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("Файл больше допустимого размера")
    return data


def multipart_body(
    fields: dict[str, str], *, file_field: str, filename: str, content: bytes, content_type: str
) -> tuple[bytes, str]:
    """Ручной multipart/form-data (в репо urllib, без requests)."""
    import uuid

    boundary = "----hub" + uuid.uuid4().hex
    crlf = "\r\n"
    parts: list[bytes] = []
    for name, value in fields.items():
        chunk = (
            "--" + boundary + crlf
            + 'Content-Disposition: form-data; name="' + name + '"' + crlf + crlf
            + str(value) + crlf
        )
        parts.append(chunk.encode("utf-8"))
    head = (
        "--" + boundary + crlf
        + 'Content-Disposition: form-data; name="' + file_field + '"; filename="' + filename + '"' + crlf
        + "Content-Type: " + content_type + crlf + crlf
    )
    parts.append(head.encode("utf-8"))
    parts.append(content)
    parts.append((crlf + "--" + boundary + "--" + crlf).encode("utf-8"))
    return b"".join(parts), "multipart/form-data; boundary=" + boundary


def guess_content_type(filename: str, fallback: str = "application/octet-stream") -> str:
    import mimetypes

    guessed, _encoding = mimetypes.guess_type(filename)
    return guessed or fallback


def safe_filename(name: str, fallback: str = "file") -> str:
    """Имя файла без путей и управляющих символов; пустое → fallback."""
    cleaned = str(name or "").replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = "".join(ch for ch in cleaned if ch.isprintable() and ch != chr(34)).strip()
    return cleaned[:200] or fallback


def request_json_multipart(
    url: str,
    *,
    fields: dict[str, str],
    file_field: str,
    filename: str,
    content: bytes,
    content_type: str,
    headers: dict | None = None,
    proxy_url: str = "",
) -> dict:
    body, body_type = multipart_body(
        fields, file_field=file_field, filename=filename, content=content, content_type=content_type
    )
    request = urllib.request.Request(
        url, data=body, headers={**(headers or {}), "Content-Type": body_type}, method="POST"
    )
    with build_opener(proxy_url).open(request, timeout=settings.CHATBALLS_AI_REQUEST_TIMEOUT) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}
