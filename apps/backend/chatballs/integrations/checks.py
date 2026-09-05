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

import imaplib
import json
import smtplib
import urllib.error
import urllib.request

from django.conf import settings

from chatballs.integrations.proxy import build_opener

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# platform-api2.max.ru отдаёт неполную цепочку сертификата (verify failed);
# рабочий и с валидным сертификатом — platform-api.max.ru.
DEFAULT_MAX_BASE_URL = "https://platform-api.max.ru"
DEFAULT_TELEGRAM_BASE_URL = "https://api.telegram.org"

CheckResult = tuple[bool, str, dict]


def _get(url: str, *, headers: dict[str, str] | None = None, proxy_url: str = "") -> tuple[int, dict]:
    opener = build_opener(proxy_url)
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    with opener.open(request, timeout=settings.CHATBALLS_AI_REQUEST_TIMEOUT) as response:
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


def check_custom(*, secret: str, base_url: str, proxy_url: str = "") -> CheckResult:
    """Connectivity check for a generic OpenAI-compatible endpoint (ADR-HUB-0034).

    Unlike OpenRouter there is no /key identity endpoint and no model catalog we
    can trust as authoritative; we only verify the endpoint speaks the OpenAI
    shape by listing models. GET /models with Authorization: Bearer <key>.
    """
    if not secret:
        return False, "Не указан API-ключ", {}
    if not base_url:
        return False, "Не указан Base URL", {}

    base = base_url.rstrip("/")

    def run() -> CheckResult:
        status, data = _get(f"{base}/models", headers={"Authorization": f"Bearer {secret}"}, proxy_url=proxy_url)
        if status != 200:
            return False, f"Эндпоинт ответил {status}", {}
        # OpenAI shape: {"data": [{"id": "..."}, ...]}. Каталог не является
        # разрешительным списком (ADR-HUB-0020:89), ответственность за model
        # identifier лежит на владельце (ADR-HUB-0034 §4).
        count = len(data.get("data") or [])
        return True, f"Эндпоинт отвечает: {count} моделей", {}

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


def _describe_mail_error(error: Exception) -> str:
    # imaplib/smtplib кладут в args байтовые ответы сервера — декодируем,
    # чтобы в статусе интеграции не светился Python-репр вида b'...'.
    parts = [part.decode("utf-8", "replace") if isinstance(part, bytes) else str(part) for part in (error.args or [])]
    return " ".join(p for p in parts if p) or str(error)


def check_email(*, secret: str, config: dict) -> CheckResult:
    """Email-подключение (ADR-HUB-0035): проверка проходит только если успешны
    ОБЕ стороны — IMAP (login + SELECT INBOX) и SMTP (EHLO + login)."""
    address = str(config.get("email", "")).strip().lower()
    imap_host = str(config.get("imap_host", "")).strip()
    smtp_host = str(config.get("smtp_host", "")).strip()
    if not secret:
        return False, "Не указан пароль ящика", {}
    if not address or not imap_host or not smtp_host:
        return False, "Не заполнены адрес, IMAP- или SMTP-хост", {}
    timeout = settings.CHATBALLS_AI_REQUEST_TIMEOUT

    try:
        imap_port = int(config.get("imap_port") or 993)
        client = (
            imaplib.IMAP4_SSL(imap_host, imap_port, timeout=timeout)
            if config.get("imap_ssl", True)
            else imaplib.IMAP4(imap_host, imap_port, timeout=timeout)
        )
        try:
            client.login(address, secret)
            client.select("INBOX", readonly=True)
        finally:
            try:
                client.logout()
            except (imaplib.IMAP4.error, OSError):
                pass
    except (imaplib.IMAP4.error, OSError, TimeoutError) as error:
        return False, f"IMAP: {_describe_mail_error(error)}", {}

    try:
        smtp_port = int(config.get("smtp_port") or 465)
        if config.get("smtp_ssl", True):
            smtp = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=timeout)
        else:
            smtp = smtplib.SMTP(smtp_host, smtp_port, timeout=timeout)
            smtp.starttls()
        with smtp:
            smtp.login(address, secret)
    except (smtplib.SMTPException, OSError, TimeoutError) as error:
        return False, f"SMTP: {_describe_mail_error(error)}", {}

    return True, f"Email: {address}", {}


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


def check_demo(*, secret: str, base_url: str, proxy_url: str = "") -> CheckResult:
    """Демо-провайдер не ходит в сеть — всегда готов."""
    return True, "Демо-провайдер: отвечает по знаниям агента, без внешних запросов и ключей", {}
