"""Connectivity checks for integrations (ADR-CHATBALLS-0020).

Stdlib-only HTTP. Each provider has a DIFFERENT API — auth, base URL and the
identity method are not interchangeable:

- OpenRouter: GET {base}/key, header `Authorization: Bearer <key>`.
- Telegram:   GET {base}/bot<token>/getMe (token in the path).
- MAX:        GET {base}/me, header `Authorization: <token>` (raw token; the
              query-param access_token is no longer supported).
- VK:         GET {base}/groups.getById + groups.getLongPollSettings, token in
              the query string (VK has no auth header); errors come back with
              HTTP 200 and an `error` body.

Each check returns (ok, detail, meta) and never raises; meta may carry
{"bot_username": ...} parsed from the provider's identity response.
"""

from __future__ import annotations

import imaplib
import json
import logging
import re
import smtplib
import urllib.error
import urllib.request
from urllib.parse import urlencode

from django.conf import settings

from chatballs.i18n import t, tn
from chatballs.integrations.openai_urls import normalize_base_url
from chatballs.integrations.outbound import mask_url_secrets
from chatballs.integrations.proxy import build_opener

logger = logging.getLogger(__name__)

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# platform-api2.max.ru отдаёт неполную цепочку сертификата (verify failed);
# рабочий и с валидным сертификатом — platform-api.max.ru.
DEFAULT_MAX_BASE_URL = "https://platform-api.max.ru"
DEFAULT_TELEGRAM_BASE_URL = "https://api.telegram.org"
DEFAULT_VK_BASE_URL = "https://api.vk.com/method"
# Версия API ВКонтакте: параметр обязателен в каждом запросе.
VK_API_VERSION = "5.199"
# Метод недоступен ключу с такими правами: Bots Long Poll требует прав
# «Сообщения сообщества» и «Управление сообществом».
VK_ACCESS_DENIED = 15

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


def _post_form(url: str, body: str, *, proxy_url: str = "") -> tuple[int, dict]:
    """POST application/x-www-form-urlencoded — форма, которую ждёт ВКонтакте."""
    opener = build_opener(proxy_url)
    request = urllib.request.Request(
        url,
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with opener.open(request, timeout=settings.CHATBALLS_AI_REQUEST_TIMEOUT) as response:
        payload = response.read().decode("utf-8")
        try:
            data = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            data = {}
        return response.status, data


def _error_reason(body: str) -> str:
    """Короткая причина из ответа провайдера.

    Ответ бывает и JSON'ом провайдера, и HTML-страницей защиты перед ним —
    человеку нужна одна фраза, а не то и другое целиком.
    """
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        payload = None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or "")[:160]
        for key in ("message", "detail", "error_description"):
            if payload.get(key):
                return str(payload[key])[:160]
        if isinstance(error, str):
            return error[:160]
    text = re.sub(r"<[^>]+>", " ", body)
    text = " ".join(text.split())
    return text[:160]


def _http_failure(error: urllib.error.HTTPError) -> str:
    """Отказ провайдера словами, а не кодом.

    Голый «HTTP 403» не говорит ничего: так отвечают и на чужой ключ, и на
    запрос из закрытого региона, и на блокировку самого прокси. Причину, если
    провайдер её назвал, показываем сразу; ответ целиком уходит в журнал.
    """
    try:
        body = error.read().decode("utf-8", "replace")
    except (OSError, ValueError):
        body = ""
    logger.warning(
        "Integration check rejected: HTTP %s %s — %s",
        error.code,
        mask_url_secrets(getattr(error, "url", "")),
        body[:500],
    )
    reason = _error_reason(body)
    if reason:
        return t("integrations.check_rejected_reason", status=error.code, reason=reason)
    if error.code in (401, 403):
        return t("integrations.check_rejected_access", status=error.code)
    return t("integrations.check_rejected", status=error.code)


def _safe(fn) -> CheckResult:
    try:
        return fn()
    except urllib.error.HTTPError as error:
        return False, _http_failure(error), {}
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return False, t("integrations.check_no_connection", error=mask_url_secrets(error)), {}


def check_openrouter(*, secret: str, base_url: str, proxy_url: str = "") -> CheckResult:
    if not secret:
        return False, t("integrations.check_api_key_missing"), {}
    base = (base_url or DEFAULT_OPENROUTER_BASE_URL).rstrip("/")

    def run() -> CheckResult:
        status, data = _get(f"{base}/key", headers={"Authorization": f"Bearer {secret}"}, proxy_url=proxy_url)
        if status != 200:
            return False, t("integrations.check_provider_answered", provider="OpenRouter", status=status), {}
        label = (data.get("data") or {}).get("label") or t("integrations.check_key_accepted")
        return True, f"OpenRouter: {label}", {}

    return _safe(run)


def check_custom(*, secret: str, base_url: str, proxy_url: str = "") -> CheckResult:
    """Connectivity check for a generic OpenAI-compatible endpoint (ADR-CHATBALLS-0034).

    Unlike OpenRouter there is no /key identity endpoint and no model catalog we
    can trust as authoritative; we only verify the endpoint speaks the OpenAI
    shape by listing models. GET /models with Authorization: Bearer <key>.
    """
    if not secret:
        return False, t("integrations.check_api_key_missing"), {}
    if not base_url:
        return False, t("integrations.check_base_url_missing"), {}

    base = normalize_base_url(base_url)

    def run() -> CheckResult:
        status, data = _get(f"{base}/models", headers={"Authorization": f"Bearer {secret}"}, proxy_url=proxy_url)
        if status != 200:
            return False, t("integrations.check_endpoint_answered", status=status), {}
        # OpenAI shape: {"data": [{"id": "..."}, ...]}. Каталог не является
        # разрешительным списком (ADR-CHATBALLS-0020:89), ответственность за model
        # identifier лежит на владельце (ADR-CHATBALLS-0034 §4).
        count = len(data.get("data") or [])
        return True, tn("integrations.check_endpoint_models", count), {}

    return _safe(run)


def check_max(*, secret: str, base_url: str, proxy_url: str = "") -> CheckResult:
    if not secret:
        return False, t("integrations.check_bot_token_missing"), {}
    base = (base_url or DEFAULT_MAX_BASE_URL).rstrip("/")

    def run() -> CheckResult:
        # MAX: токен в заголовке Authorization (без Bearer), метод GET /me.
        status, data = _get(f"{base}/me", headers={"Authorization": secret}, proxy_url=proxy_url)
        if status != 200:
            return False, t("integrations.check_provider_answered", provider="MAX", status=status), {}
        bot_id = data.get("user_id")
        username = data.get("username") or ""
        name = data.get("name") or username or t("integrations.check_bot_connected")
        meta = {"bot_id": str(bot_id) if bot_id else "", "bot_username": username, "bot_name": name}
        return True, f"MAX: {name}", meta

    return _safe(run)


def _describe_mail_error(error: Exception) -> str:
    # imaplib/smtplib кладут в args байтовые ответы сервера — декодируем,
    # чтобы в статусе интеграции не светился Python-репр вида b'...'.
    parts = [part.decode("utf-8", "replace") if isinstance(part, bytes) else str(part) for part in (error.args or [])]
    return " ".join(p for p in parts if p) or str(error)


def check_email(*, secret: str, config: dict) -> CheckResult:
    """Email-подключение (ADR-CHATBALLS-0035): проверка проходит только если успешны
    ОБЕ стороны — IMAP (login + SELECT INBOX) и SMTP (EHLO + login)."""
    address = str(config.get("email", "")).strip().lower()
    imap_host = str(config.get("imap_host", "")).strip()
    smtp_host = str(config.get("smtp_host", "")).strip()
    if not secret:
        return False, t("integrations.check_mailbox_password_missing"), {}
    if not address or not imap_host or not smtp_host:
        return False, t("integrations.check_mail_hosts_missing"), {}
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
        return False, t("integrations.check_bot_token_missing"), {}
    base = (base_url or DEFAULT_TELEGRAM_BASE_URL).rstrip("/")

    def run() -> CheckResult:
        # Telegram: токен в пути /bot<token>/getMe.
        status, data = _get(f"{base}/bot{secret}/getMe", proxy_url=proxy_url)
        if status != 200 or not data.get("ok"):
            return False, t("integrations.check_provider_answered", provider="Telegram", status=status), {}
        result = data.get("result") or {}
        bot_id = result.get("id")
        username = result.get("username") or ""
        name = result.get("first_name") or username or "бот подключён"
        meta = {"bot_id": str(bot_id) if bot_id else "", "bot_username": username, "bot_name": name}
        detail = f"Telegram: @{username}" if username else f'Telegram: {t("integrations.check_bot_connected")}'
        return True, detail, meta

    return _safe(run)


class VkRejected(Exception):
    """ВКонтакте отклонил запрос: текст уже пригоден для показа человеку."""

    def __init__(self, message: str, code: int = 0) -> None:
        super().__init__(message)
        self.code = code


def vk_call(*, base_url: str, method: str, secret: str, params: dict | None = None, proxy_url: str = "", post: bool = False):
    """Вызов метода API ВКонтакте; возвращает содержимое поля response.

    Токен уходит параметром запроса — заголовка авторизации у ВКонтакте нет.
    Поэтому адрес нигде не печатается как есть: и журнал, и статус подключения
    получают его через ``mask_url_secrets``.

    Ошибку ВКонтакте отдаёт кодом 200 и телом ``error``, так что проверять
    статус недостаточно: отозванный токен выглядел бы успешной проверкой.
    """
    base = (base_url or DEFAULT_VK_BASE_URL).rstrip("/")
    query = urlencode({**(params or {}), "access_token": secret, "v": VK_API_VERSION})
    if post:
        status, data = _post_form(f"{base}/{method}", query, proxy_url=proxy_url)
    else:
        status, data = _get(f"{base}/{method}?{query}", proxy_url=proxy_url)
    error = data.get("error")
    if isinstance(error, dict):
        raise VkRejected(
            t(
                "integrations.check_vk_rejected",
                code=error.get("error_code", ""),
                reason=str(error.get("error_msg") or "")[:160],
            ),
            code=int(error.get("error_code") or 0),
        )
    if status != 200:
        raise VkRejected(t("integrations.check_provider_answered", provider="ВКонтакте", status=status))
    return data.get("response")


def vk_group(response) -> dict:
    """Сообщество из ответа groups.getById.

    Форма ответа зависит от версии API: до 5.199 это список, дальше объект с
    полем groups. Подключение переживает обе.
    """
    items = response.get("groups") if isinstance(response, dict) else response
    first_group = (items or [None])[0] if isinstance(items, list) else None
    return first_group if isinstance(first_group, dict) else {}


def check_vk(*, secret: str, base_url: str, proxy_url: str = "") -> CheckResult:
    """Сообщество ВКонтакте: кто мы и включён ли приём сообщений.

    Ключ доступа сообщества сам называет сообщество, поэтому его идентификатор
    владельцу вводить не нужно — как имя бота у Telegram и MAX, он попадает в
    конфигурацию результатом проверки.

    Выключенный Long Poll — это ошибка подключения: принимать сообщения в таком
    состоянии невозможно. Включаем не мы: настройки чужого сообщества меняет
    его владелец.
    """
    if not secret:
        return False, t("integrations.check_bot_token_missing"), {}

    def run() -> CheckResult:
        try:
            group = vk_group(vk_call(base_url=base_url, method="groups.getById", secret=secret, proxy_url=proxy_url))
            if not group.get("id"):
                return False, t("integrations.check_vk_no_group"), {}
            group_id = str(group["id"])
            long_poll = vk_call(
                base_url=base_url,
                method="groups.getLongPollSettings",
                secret=secret,
                params={"group_id": group_id},
                proxy_url=proxy_url,
            )
        except VkRejected as error:
            # 15 — метод недоступен ключу с такими правами. Без подсказки
            # владелец видел бы английское «no access» и не знал, что чинить.
            if error.code == VK_ACCESS_DENIED:
                return False, t("integrations.check_vk_scopes"), {}
            return False, str(error), {}
        name = str(group.get("name") or "")
        screen_name = str(group.get("screen_name") or "")
        meta = {"bot_id": group_id, "bot_username": screen_name, "bot_name": name or screen_name}
        settings_payload = long_poll if isinstance(long_poll, dict) else {}
        if not settings_payload.get("is_enabled"):
            return False, t("integrations.check_vk_longpoll_off"), meta
        if not (settings_payload.get("events") or {}).get("message_new"):
            return False, t("integrations.check_vk_message_event_off"), meta
        return True, f"ВКонтакте: {name or screen_name}", meta

    return _safe(run)


def check_demo(*, secret: str, base_url: str, proxy_url: str = "") -> CheckResult:
    """Демо-провайдер не ходит в сеть — всегда готов."""
    return True, t("integrations.check_demo"), {}
