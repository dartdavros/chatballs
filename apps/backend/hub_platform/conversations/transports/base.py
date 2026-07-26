"""Shared transport primitives (M2): normalized inbound message + HTTP with
optional per-connection proxy (config["proxy_url"], e.g. http://host:port или
socks5://host:port). HTTP/HTTPS/SOCKS5 — единый opener в integrations.proxy."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from django.conf import settings

from hub_platform.integrations.proxy import build_opener


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
    # Безопасный форматированный вариант входящего письма. Plain text остаётся
    # обязательным fallback для AI, поиска, уведомлений и превью.
    content_html: str = ""
    # Транспортная мета для тредирования ответа (email: subject/last_message_id).
    # Пишется в Conversation.transport_meta при ingest (ADR-HUB-0035).
    thread_meta: dict | None = None


def request_json(url: str, *, headers: dict | None = None, method: str = "GET", body: dict | None = None, proxy_url: str = "") -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with build_opener(proxy_url).open(request, timeout=settings.CUS_AI_REQUEST_TIMEOUT) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def first(d: dict, *keys, default=None):
    for key in keys:
        value = d.get(key)
        if value not in (None, ""):
            return value
    return default
