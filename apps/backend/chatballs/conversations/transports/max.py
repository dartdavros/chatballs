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
import time
import urllib.error
import urllib.parse

from django.conf import settings

from chatballs.conversations.transports.base import (
    InboundFile,
    InboundMessage,
    download_bytes,
    first,
    guess_content_type,
    request_json,
    request_json_multipart,
    safe_filename,
)
from chatballs.integrations.checks import DEFAULT_MAX_BASE_URL
from chatballs.integrations.outbound import host_of

logger = logging.getLogger(__name__)


def _base(integration) -> str:
    return (integration.config.get("base_url") or DEFAULT_MAX_BASE_URL).rstrip("/")


def _proxy(integration) -> str:
    return integration.config.get("proxy_url", "")


def _download_host(integration) -> str:
    """Хост подключения: ссылки вложений разрешено брать и с него.

    MAX отдаёт вложения с адреса в ответе, и по умолчанию это публичный CDN.
    Но self-hosted мог указать в base_url собственный сервер внутри сети —
    этот хост владелец назвал сам, поэтому он остаётся разрешённым.
    """
    return host_of(_base(integration))


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
    files = _file_attachments(inner)
    if (not text and not phone and not voice_url and not files) or user_id is None or external_id is None:
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
        files=files,
    )


def _file_attachments(inner: dict) -> tuple[InboundFile, ...]:
    """Файлы и фото MAX: attachments[type=file|image] с payload.url (у фото —
    payload.photos{...url} или payload.url)."""
    files: list[InboundFile] = []
    for attachment in inner.get("attachments") or []:
        kind = attachment.get("type")
        payload = attachment.get("payload") or {}
        if kind == "file":
            url = str(first(payload, "url", "download_url", default=""))
            if not url:
                continue
            name = safe_filename(first(attachment, "filename", "name", default="") or first(payload, "filename", "name", default=""), "document")
            mime = guess_content_type(name)
            files.append(InboundFile(name=name, content_type=mime, size=int(first(attachment, "size", default=0) or payload.get("size") or 0), url=url, is_image=mime.startswith("image/")))
        elif kind == "video":
            url = str(first(payload, "url", "download_url", default=""))
            if url:
                files.append(InboundFile(name="video.mp4", content_type="video/mp4", url=url))
        elif kind == "image":
            url = str(first(payload, "url", "download_url", default=""))
            if not url:
                photos = payload.get("photos") or {}
                for entry in photos.values() if isinstance(photos, dict) else photos:
                    candidate = str((entry or {}).get("url") or "")
                    if candidate:
                        url = candidate
                        break
            if not url:
                continue
            files.append(InboundFile(name="photo.jpg", content_type="image/jpeg", url=url, is_image=True))
    return tuple(files)


def download_file(integration, url: str, content_type: str) -> tuple[bytes, str]:
    """Скачивание файла/фото MAX по прямому URL вложения."""
    return (
        download_bytes(url, proxy_url=_proxy(integration), allowed_host=_download_host(integration)),
        content_type or "application/octet-stream",
    )


def send_file(integration, *, chat_id: str, user_id: str, content: bytes, filename: str, content_type: str, caption: str = "") -> bool:
    """Отправка файла оператора: /uploads?type=file|image -> multipart -> attachment token."""
    token = integration.secret
    if not token or not (chat_id or user_id):
        return False
    as_image = content_type in ("image/jpeg", "image/png", "image/gif", "image/webp")
    upload_type = "image" if as_image else "file"
    try:
        upload = request_json(
            f"{_base(integration)}/uploads?type={upload_type}",
            headers={"Authorization": token, "Content-Type": "application/json"},
            method="POST",
            body={},
            proxy_url=_proxy(integration),
        )
        upload_url = str(upload.get("url") or "")
        if not upload_url:
            return False
        uploaded = request_json_multipart(
            upload_url,
            fields={},
            file_field="data",
            filename=filename,
            content=content,
            content_type=content_type,
            proxy_url=_proxy(integration),
        )
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, json.JSONDecodeError) as error:
        logger.warning("MAX file upload failed for integration %s: %s", integration.id, error)
        return False
    if as_image:
        # У фото сервер загрузки отвечает {"photos": {key: {"token": ...}}}.
        photos = uploaded.get("photos") or {}
        tokens = [str((entry or {}).get("token") or "") for entry in (photos.values() if isinstance(photos, dict) else [])]
        attach_payload = {"photos": photos} if any(tokens) else {"token": str(uploaded.get("token") or "")}
        if not any(tokens) and not attach_payload["token"]:
            return False
    else:
        attach_token = str(uploaded.get("token") or "")
        if not attach_token:
            return False
        attach_payload = {"token": attach_token}
    body = {"attachments": [{"type": upload_type, "payload": attach_payload}], **({"text": caption[:4000]} if caption else {})}
    for attempt in range(3):
        if attempt:
            time.sleep(1)
        if _send(integration, chat_id=chat_id, user_id=user_id, body=body):
            return True
    return False


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
    params = {"timeout": settings.CHATBALLS_MESSENGER_POLL_TIMEOUT_SECONDS, "limit": 100}
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
    content = download_bytes(
        url, proxy_url=_proxy(integration), allowed_host=_download_host(integration)
    )
    return content, "audio/ogg"


def send_voice(integration, *, chat_id: str, user_id: str, content: bytes, content_type: str, duration: int) -> bool:
    """Отправка голосового оператора: /uploads?type=audio -> multipart -> attachment token."""
    token = integration.secret
    if not token or not (chat_id or user_id):
        return False
    suffix = (content_type.rsplit("/", 1)[-1] or "ogg").split(";")[0]
    try:
        upload = request_json(
            f"{_base(integration)}/uploads?type=audio",
            headers={"Authorization": token, "Content-Type": "application/json"},
            method="POST",
            body={},
            proxy_url=_proxy(integration),
        )
        upload_url = str(upload.get("url") or "")
        if not upload_url:
            return False
        uploaded = request_json_multipart(
            upload_url,
            fields={},
            file_field="data",
            filename=f"voice.{suffix}",
            content=content,
            content_type=content_type,
            proxy_url=_proxy(integration),
        )
        attach_token = str(uploaded.get("token") or "")
        if not attach_token:
            return False
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, json.JSONDecodeError) as error:
        logger.warning("MAX voice upload failed for integration %s: %s", integration.id, error)
        return False
    body = {"attachments": [{"type": "audio", "payload": {"token": attach_token}}]}
    # Сразу после загрузки MAX может ответить attachment.not.ready — файл ещё
    # обрабатывается на его стороне; даём пару повторов с паузой.
    for attempt in range(3):
        if attempt:
            time.sleep(1)
        if _send(integration, chat_id=chat_id, user_id=user_id, body=body):
            return True
    return False
