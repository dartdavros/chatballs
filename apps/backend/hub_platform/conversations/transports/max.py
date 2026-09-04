"""MAX bot transport (M2, ADR-HUB-0020).

Long polling for inbound updates and text sending. MAX (TamTam heritage) field
naming is not fully documented, so inbound parsing is defensive and the raw
update is logged so the live shape can be confirmed.
"""

from __future__ import annotations

import http.client
import json
import logging
import re
import urllib.error
import urllib.parse

from django.conf import settings

from hub_platform.conversations.transports.base import InboundMessage, download_bytes, first, request_json
from hub_platform.integrations.checks import DEFAULT_MAX_BASE_URL

logger = logging.getLogger(__name__)


def _base(integration) -> str:
    return (integration.config.get("base_url") or DEFAULT_MAX_BASE_URL).rstrip("/")


def _proxy(integration) -> str:
    return integration.config.get("proxy_url", "")


def _contact_phone(inner: dict, msg: dict) -> str:
    # Ответ на кнопку request_contact: attachment типа contact. Телефон либо
    # прямым полем, либо внутри vCard (vcf_info) — парсим оба варианта.
    attachments = inner.get("attachments") or msg.get("attachments") or []
    for attachment in attachments:
        if str(attachment.get("type") or "").lower() != "contact":
            continue
        payload = attachment.get("payload") or {}
        phone = first(payload, "phone", "phone_number", "phoneNumber")
        if phone:
            return str(phone)
        vcf = str(first(payload, "vcf_info", "vcfInfo", default=""))
        match = re.search(r"TEL[^:]*:([+\d][\d\-\s().]{3,})", vcf, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _bot_started(update: dict) -> InboundMessage | None:
    # Нажатие «Начать» (в т.ч. по deep-link): payload из ?start=<...> приходит
    # не сообщением, а отдельным апдейтом bot_started. Нормализуем в «/start
    # <payload>» — как присылает Telegram, дальше единая обработка.
    sender = update.get("user") or {}
    user_id = first(sender, "user_id", "userId", "id")
    chat_id = first(update, "chat_id", "chatId")
    external_id = first(update, "update_id", "updateId", "timestamp")
    if user_id is None or external_id is None:
        return None
    payload = str(first(update, "payload", default="") or "")
    return InboundMessage(
        external_id=str(external_id),
        user_id=str(user_id),
        chat_id="" if chat_id is None else str(chat_id),
        text=f"/start {payload}".strip(),
        display_name=str(first(sender, "name", "display_name", default="")),
        username=str(first(sender, "username", "user_name", default="")),
        avatar_url=str(first(sender, "avatar_url", "avatar", default="")),
    )


def _normalize(update: dict) -> InboundMessage | None:
    logger.info("MAX raw update: %s", json.dumps(update, ensure_ascii=False))
    update_type = update.get("update_type") or update.get("updateType")
    if update_type == "bot_started":
        return _bot_started(update)
    if update_type not in (None, "message_created"):
        return None
    msg = update.get("message") or update.get("payload") or {}
    inner = msg.get("body") or msg.get("message") or msg
    text = first(inner, "text") or first(msg, "text") or ""
    sender = msg.get("sender") or inner.get("sender") or {}
    user_id = first(sender, "user_id", "userId", "id") or first(msg, "from_id")
    recipient = msg.get("recipient") or msg.get("chat") or {}
    chat_id = first(recipient, "chat_id", "chatId")
    external_id = first(inner, "mid", "msgId", "seq") or first(update, "update_id", "updateId", "timestamp")
    phone = _contact_phone(inner, msg)
    voice_url, voice_duration = _voice_attachment(inner)
    if (not text and not phone and not voice_url) or user_id is None or external_id is None:
        return None
    return InboundMessage(
        external_id=str(external_id),
        user_id=str(user_id),
        chat_id="" if chat_id is None else str(chat_id),
        text=str(text),
        display_name=str(first(sender, "name", "display_name", default="")),
        username=str(first(sender, "username", "user_name", default="")),
        phone=phone,
        avatar_url=str(first(sender, "avatar_url", "avatar", default="")),
        voice_url=voice_url,
        voice_duration=voice_duration,
        voice_mime="audio/ogg" if voice_url else "",
    )


def _voice_attachment(inner: dict) -> tuple[str, int]:
    """Голосовое/аудио-вложение MAX: payload.url для скачивания."""
    for attachment in inner.get("attachments") or []:
        if attachment.get("type") in ("audio", "voice"):
            payload = attachment.get("payload") or {}
            url = str(first(payload, "url", "download_url", default=""))
            if url:
                return url, int(first(attachment, "duration", default=0) or payload.get("duration") or 0)
    return "", 0


def poll_updates(integration) -> tuple[list[InboundMessage], str]:
    token = integration.secret
    if not token:
        return [], integration.poll_marker
    params = {"timeout": settings.CUS_MESSENGER_POLL_TIMEOUT_SECONDS, "limit": 100}
    if integration.poll_marker:
        params["marker"] = integration.poll_marker
    url = f"{_base(integration)}/updates?{urllib.parse.urlencode(params)}"
    try:
        data = request_json(url, headers={"Authorization": token, "Content-Type": "application/json"}, proxy_url=_proxy(integration))
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, json.JSONDecodeError) as error:
        logger.warning("MAX poll failed for integration %s: %s", integration.id, error)
        return [], integration.poll_marker
    updates = data.get("updates") or []
    messages = [m for m in (_normalize(u) for u in updates) if m is not None]
    new_marker = data.get("marker")
    return messages, ("" if new_marker is None else str(new_marker))


def _send(integration, *, chat_id: str, user_id: str, body: dict) -> bool:
    token = integration.secret
    if not token:
        return False
    query = {}
    if chat_id:
        query["chat_id"] = chat_id
    elif user_id:
        query["user_id"] = user_id
    url = f"{_base(integration)}/messages?{urllib.parse.urlencode(query)}"
    try:
        request_json(url, headers={"Authorization": token, "Content-Type": "application/json"}, method="POST", body=body, proxy_url=_proxy(integration))
        return True
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, json.JSONDecodeError) as error:
        logger.warning("MAX send failed for integration %s: %s", integration.id, error)
        return False


def send_text(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    return _send(integration, chat_id=chat_id, user_id=user_id, body={"text": text})


def send_contact_request(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    # Inline-клавиатура с кнопкой request_contact (Bot API MAX/TamTam).
    keyboard = {
        "type": "inline_keyboard",
        "payload": {"buttons": [[{"type": "request_contact", "text": "Поделиться контактом"}]]},
    }
    return _send(integration, chat_id=chat_id, user_id=user_id, body={"text": text, "attachments": [keyboard]})


def send_call_invite(integration, *, chat_id: str, user_id: str, text: str, url: str) -> bool:
    # Приглашение на онлайн-звонок: inline-кнопка со ссылкой /calls/<token>.
    keyboard = {
        "type": "inline_keyboard",
        "payload": {"buttons": [[{"type": "link", "text": "Перейти к звонку", "url": url}]]},
    }
    return _send(integration, chat_id=chat_id, user_id=user_id, body={"text": text, "attachments": [keyboard]})


def download_voice(integration, url: str) -> tuple[bytes, str]:
    """Скачивание голосового MAX по прямому URL вложения."""
    content = download_bytes(url, proxy_url=_proxy(integration))
    return content, "audio/ogg"
