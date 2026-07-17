"""Telegram bot transport (M2, ADR-HUB-0020).

Long polling via getUpdates (offset cursor) and sendMessage. Token goes in the
path. Optional per-connection proxy via config["proxy_url"] (Telegram is often
unreachable without one).
"""

from __future__ import annotations

import http.client
import json
import logging
import urllib.error

from django.conf import settings

from hub_platform.conversations.transports.base import InboundMessage, request_json
from hub_platform.integrations.checks import DEFAULT_TELEGRAM_BASE_URL

logger = logging.getLogger(__name__)


def _base(integration) -> str:
    return (integration.config.get("base_url") or DEFAULT_TELEGRAM_BASE_URL).rstrip("/")


def _proxy(integration) -> str:
    return integration.config.get("proxy_url", "")


def _normalize(update: dict) -> InboundMessage | None:
    message = update.get("message") or update.get("edited_message") or {}
    text = message.get("text") or ""
    sender = message.get("from") or {}
    chat = message.get("chat") or {}
    # Контакт приходит отдельным сообщением без текста (ответ на request_contact).
    phone = str((message.get("contact") or {}).get("phone_number") or "")
    if (not text and not phone) or "id" not in sender or "id" not in chat:
        return None
    name = " ".join(p for p in [sender.get("first_name"), sender.get("last_name")] if p) or sender.get("username") or ""
    return InboundMessage(
        external_id=str(update.get("update_id")),
        user_id=str(sender["id"]),
        chat_id=str(chat["id"]),
        text=str(text),
        display_name=str(name),
        username=str(sender.get("username") or ""),
        phone=phone,
    )


def poll_updates(integration) -> tuple[list[InboundMessage], str]:
    token = integration.secret
    if not token:
        return [], integration.poll_marker
    offset = integration.poll_marker or ""
    url = f"{_base(integration)}/bot{token}/getUpdates?timeout={settings.CUS_MESSENGER_POLL_TIMEOUT_SECONDS}&limit=100"
    if offset:
        url += f"&offset={offset}"
    try:
        data = request_json(url, proxy_url=_proxy(integration))
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, json.JSONDecodeError) as error:
        logger.warning("Telegram poll failed for integration %s: %s", integration.id, error)
        return [], integration.poll_marker
    if not data.get("ok"):
        return [], integration.poll_marker
    updates = data.get("result") or []
    messages = [m for m in (_normalize(u) for u in updates) if m is not None]
    max_update_id = max((u.get("update_id", 0) for u in updates), default=None)
    new_marker = str(max_update_id + 1) if max_update_id is not None else integration.poll_marker
    return messages, new_marker


def _send(integration, *, chat_id: str, user_id: str, body: dict) -> bool:
    token = integration.secret
    target = chat_id or user_id
    if not token or not target:
        return False
    url = f"{_base(integration)}/bot{token}/sendMessage"
    try:
        request_json(url, headers={"Content-Type": "application/json"}, method="POST", body={"chat_id": target, **body}, proxy_url=_proxy(integration))
        return True
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, json.JSONDecodeError) as error:
        logger.warning("Telegram send failed for integration %s: %s", integration.id, error)
        return False


def send_text(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    return _send(integration, chat_id=chat_id, user_id=user_id, body={"text": text})


def send_contact_request(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    # Reply-клавиатура с request_contact: телефон бот получает только так.
    keyboard = {
        "keyboard": [[{"text": "Поделиться контактом", "request_contact": True}]],
        "one_time_keyboard": True,
        "resize_keyboard": True,
    }
    return _send(integration, chat_id=chat_id, user_id=user_id, body={"text": text, "reply_markup": keyboard})


def send_contact_ack(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    # Подтверждение + снятие reply-клавиатуры, чтобы кнопка не висела у клиента.
    return _send(integration, chat_id=chat_id, user_id=user_id, body={"text": text, "reply_markup": {"remove_keyboard": True}})


def send_call_invite(integration, *, chat_id: str, user_id: str, text: str, url: str) -> bool:
    # Приглашение на онлайн-звонок: inline-кнопка со ссылкой /calls/<token>.
    keyboard = {"inline_keyboard": [[{"text": "Перейти к звонку", "url": url}]]}
    return _send(integration, chat_id=chat_id, user_id=user_id, body={"text": text, "reply_markup": keyboard})
