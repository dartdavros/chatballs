"""Shared transport primitives (M2): normalized inbound message + HTTP with
optional per-connection proxy (config["proxy_url"], e.g. http://host:port).
SOCKS would require an extra dependency; HTTP/HTTPS proxies work via stdlib."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class InboundMessage:
    external_id: str
    user_id: str
    chat_id: str
    text: str
    display_name: str


def _opener(proxy_url: str):
    handlers = []
    if proxy_url:
        handlers.append(urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}))
    return urllib.request.build_opener(*handlers)


def request_json(url: str, *, headers: dict | None = None, method: str = "GET", body: dict | None = None, proxy_url: str = "") -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with _opener(proxy_url).open(request, timeout=settings.HUB_AI_REQUEST_TIMEOUT) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def first(d: dict, *keys, default=None):
    for key in keys:
        value = d.get(key)
        if value not in (None, ""):
            return value
    return default
