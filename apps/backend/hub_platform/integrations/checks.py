"""Connectivity checks for integrations (ADR-HUB-0020).

Stdlib-only HTTP, mirroring hub_platform.ai.provider.openrouter. Each check
returns (ok, detail) and never raises: failures become an ERROR status with a
human-readable message shown in the UI.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MAX_BASE_URL = "https://botapi.max.ru"
DEFAULT_TELEGRAM_BASE_URL = "https://api.telegram.org"


def _get(url: str, *, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(request, timeout=settings.HUB_AI_REQUEST_TIMEOUT) as response:
        body = response.read().decode("utf-8")
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}
        return response.status, data


def _safe(fn) -> tuple[bool, str]:
    try:
        return fn()
    except urllib.error.HTTPError as error:
        return False, f"HTTP {error.code}: {error.reason}"
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return False, f"Нет связи: {error}"


def check_openrouter(*, secret: str, base_url: str) -> tuple[bool, str]:
    if not secret:
        return False, "Не указан API-ключ"
    base = (base_url or DEFAULT_OPENROUTER_BASE_URL).rstrip("/")

    def run() -> tuple[bool, str]:
        status, data = _get(f"{base}/key", headers={"Authorization": f"Bearer {secret}"})
        if status != 200:
            return False, f"OpenRouter ответил {status}"
        label = (data.get("data") or {}).get("label") or "ключ принят"
        return True, f"OpenRouter: {label}"

    return _safe(run)


def check_max(*, secret: str, base_url: str) -> tuple[bool, str]:
    if not secret:
        return False, "Не указан токен бота"
    base = (base_url or DEFAULT_MAX_BASE_URL).rstrip("/")

    def run() -> tuple[bool, str]:
        status, data = _get(f"{base}/me?access_token={urllib.parse.quote(secret)}")
        if status != 200:
            return False, f"MAX ответил {status}"
        name = data.get("name") or data.get("username") or "бот подключён"
        return True, f"MAX: {name}"

    return _safe(run)


def check_telegram(*, secret: str, base_url: str) -> tuple[bool, str]:
    if not secret:
        return False, "Не указан токен бота"
    base = (base_url or DEFAULT_TELEGRAM_BASE_URL).rstrip("/")

    def run() -> tuple[bool, str]:
        status, data = _get(f"{base}/bot{secret}/getMe")
        if status != 200 or not data.get("ok"):
            return False, f"Telegram ответил {status}"
        username = (data.get("result") or {}).get("username") or "бот подключён"
        return True, f"Telegram: @{username}"

    return _safe(run)
