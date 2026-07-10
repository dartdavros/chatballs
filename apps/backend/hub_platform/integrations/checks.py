"""Connectivity checks for integrations (ADR-HUB-0020).

Stdlib-only HTTP. Each provider has a DIFFERENT API — auth, base URL and the
identity method are not interchangeable:

- OpenRouter: GET {base}/key, header `Authorization: Bearer <key>`.
- Telegram:   GET {base}/bot<token>/getMe (token in the path).
- MAX:        GET {base}/me, header `Authorization: <token>` (raw token; the
              query-param access_token is no longer supported).

Each check returns (ok, detail, meta) and never raises; meta may carry
{"bot_username": ...} parsed from the provider's identity response.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from django.conf import settings

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# platform-api2.max.ru отдаёт неполную цепочку сертификата (verify failed);
# рабочий и с валидным сертификатом — platform-api.max.ru.
DEFAULT_MAX_BASE_URL = "https://platform-api.max.ru"
DEFAULT_TELEGRAM_BASE_URL = "https://api.telegram.org"

CheckResult = tuple[bool, str, dict]


def _get(url: str, *, headers: dict[str, str] | None = None, proxy_url: str = "") -> tuple[int, dict]:
    handlers = []
    if proxy_url:
        handlers.append(urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}))
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    with opener.open(request, timeout=settings.HUB_AI_REQUEST_TIMEOUT) as response:
        body = response.read().decode("utf-8")
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}
        return response.status, data


def _safe(fn) -> CheckResult:
    try:
        return fn()
    except urllib.error.HTTPError as error:
        return False, f"HTTP {error.code}: {error.reason}", {}
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return False, f"Нет связи: {error}", {}


def check_openrouter(*, secret: str, base_url: str, proxy_url: str = "") -> CheckResult:
    if not secret:
        return False, "Не указан API-ключ", {}
    base = (base_url or DEFAULT_OPENROUTER_BASE_URL).rstrip("/")

    def run() -> CheckResult:
        status, data = _get(f"{base}/key", headers={"Authorization": f"Bearer {secret}"}, proxy_url=proxy_url)
        if status != 200:
            return False, f"OpenRouter ответил {status}", {}
        label = (data.get("data") or {}).get("label") or "ключ принят"
        return True, f"OpenRouter: {label}", {}

    return _safe(run)


def check_max(*, secret: str, base_url: str, proxy_url: str = "") -> CheckResult:
    if not secret:
        return False, "Не указан токен бота", {}
    base = (base_url or DEFAULT_MAX_BASE_URL).rstrip("/")

    def run() -> CheckResult:
        # MAX: токен в заголовке Authorization (без Bearer), метод GET /me.
        status, data = _get(f"{base}/me", headers={"Authorization": secret}, proxy_url=proxy_url)
        if status != 200:
            return False, f"MAX ответил {status}", {}
        bot_id = data.get("user_id")
        username = data.get("username") or ""
        name = data.get("name") or username or "бот подключён"
        meta = {"bot_id": str(bot_id) if bot_id else "", "bot_username": username, "bot_name": name}
        return True, f"MAX: {name}", meta

    return _safe(run)


def check_telegram(*, secret: str, base_url: str, proxy_url: str = "") -> CheckResult:
    if not secret:
        return False, "Не указан токен бота", {}
    base = (base_url or DEFAULT_TELEGRAM_BASE_URL).rstrip("/")

    def run() -> CheckResult:
        # Telegram: токен в пути /bot<token>/getMe.
        status, data = _get(f"{base}/bot{secret}/getMe", proxy_url=proxy_url)
        if status != 200 or not data.get("ok"):
            return False, f"Telegram ответил {status}", {}
        result = data.get("result") or {}
        bot_id = result.get("id")
        username = result.get("username") or ""
        name = result.get("first_name") or username or "бот подключён"
        meta = {"bot_id": str(bot_id) if bot_id else "", "bot_username": username, "bot_name": name}
        detail = f"Telegram: @{username}" if username else "Telegram: бот подключён"
        return True, detail, meta

    return _safe(run)
