"""Telegram bot transport (M2, ADR-CHATBALLS-0020).

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

from chatballs.conversations.transports.base import (
    InboundFile,
    InboundMessage,
    download_bytes,
    guess_content_type,
    request_json,
    request_json_multipart,
    safe_filename,
)
from chatballs.conversations.transports.errors import PollFailed
from chatballs.i18n import customer_language, t
from chatballs.integrations.checks import DEFAULT_TELEGRAM_BASE_URL
from chatballs.integrations.outbound import host_of

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
    # Голосовое (дизайн-базлайн v2): file_id скачивается в ingest через getFile.
    voice = message.get("voice") or {}
    voice_file_id = str(voice.get("file_id") or "")
    files = _files(message)
    if files and not text:
        # Подпись к файлу/фото — текст сообщения.
        text = message.get("caption") or ""
    if (not text and not phone and not voice_file_id and not files) or "id" not in sender or "id" not in chat:
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
        voice_file_id=voice_file_id,
        voice_duration=int(voice.get("duration") or 0),
        voice_mime=str(voice.get("mime_type") or "audio/ogg"),
        files=files,
    )


# Медиа Telegram, которые принимаем файлом: (поле, имя по умолчанию, mime по умолчанию).
_MEDIA_FIELDS = (
    ("document", "document", ""),
    ("audio", "audio.mp3", "audio/mpeg"),
    ("video", "video.mp4", "video/mp4"),
    ("video_note", "video-note.mp4", "video/mp4"),
    ("animation", "animation.mp4", "video/mp4"),
)


def _files(message: dict) -> tuple[InboundFile, ...]:
    """Документ/аудио/видео или фото (берём самый крупный размер из массива photo)."""
    for field, default_name, default_mime in _MEDIA_FIELDS:
        media = message.get(field) or {}
        if not media.get("file_id"):
            continue
        name = safe_filename(media.get("file_name") or (media.get("title") and f"{media['title']}.mp3") or "", default_name)
        mime = str(media.get("mime_type") or default_mime or guess_content_type(name))
        return (
            InboundFile(
                name=name,
                content_type=mime,
                size=int(media.get("file_size") or 0),
                file_id=str(media["file_id"]),
                is_image=mime.startswith("image/"),
            ),
        )
    photos = message.get("photo") or []
    if photos:
        best = photos[-1]
        if best.get("file_id"):
            return (
                InboundFile(
                    name="photo.jpg",
                    content_type="image/jpeg",
                    size=int(best.get("file_size") or 0),
                    file_id=str(best["file_id"]),
                    is_image=True,
                ),
            )
    return ()


def poll_updates(integration) -> tuple[list[InboundMessage], str]:
    token = integration.secret
    if not token:
        return [], integration.poll_marker
    offset = integration.poll_marker or ""
    url = f"{_base(integration)}/bot{token}/getUpdates?timeout={settings.CHATBALLS_MESSENGER_POLL_TIMEOUT_SECONDS}&limit=100"
    if offset:
        url += f"&offset={offset}"
    try:
        data = request_json(url, proxy_url=_proxy(integration))
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, json.JSONDecodeError) as error:
        raise PollFailed(str(error)) from error
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


def _caption(integration, key: str) -> str:
    """Подпись кнопки читает клиент — язык организации, а не язык запроса."""

    return t(key, language=customer_language(integration.organization))


def send_contact_request(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    # Reply-клавиатура с request_contact: телефон бот получает только так.
    keyboard = {
        "keyboard": [[{"text": _caption(integration, "conversations.button_share_contact"), "request_contact": True}]],
        "one_time_keyboard": True,
        "resize_keyboard": True,
    }
    return _send(integration, chat_id=chat_id, user_id=user_id, body={"text": text, "reply_markup": keyboard})


def send_contact_ack(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    # Подтверждение + снятие reply-клавиатуры, чтобы кнопка не висела у клиента.
    return _send(integration, chat_id=chat_id, user_id=user_id, body={"text": text, "reply_markup": {"remove_keyboard": True}})


def send_call_invite(integration, *, chat_id: str, user_id: str, text: str, url: str) -> bool:
    # Приглашение на онлайн-звонок: inline-кнопка со ссылкой /calls/<token>.
    keyboard = {"inline_keyboard": [[{"text": _caption(integration, "conversations.button_join_call"), "url": url}]]}
    return _send(integration, chat_id=chat_id, user_id=user_id, body={"text": text, "reply_markup": keyboard})


def download_file(integration, file_id: str) -> tuple[bytes, str]:
    """Скачивание файла по file_id: getFile -> file_path -> /file/bot<token>/<path>."""
    token = integration.secret
    data = request_json(
        f"{_base(integration)}/bot{token}/getFile?file_id={file_id}",
        proxy_url=_proxy(integration),
    )
    file_path = ((data.get("result") or {}).get("file_path") or "")
    if not data.get("ok") or not file_path:
        raise ValueError(t("conversations.telegram_getfile_failed"))
    content = download_bytes(
        f"{_base(integration)}/file/bot{token}/{file_path}",
        proxy_url=_proxy(integration),
        # Адрес собран из base_url подключения, а его владелец задал сам:
        # у self-hosted Bot API он может быть и внутри сети.
        allowed_host=host_of(_base(integration)),
    )
    return content, guess_content_type(file_path)


def send_file(integration, *, chat_id: str, user_id: str, content: bytes, filename: str, content_type: str, caption: str = "") -> bool:
    """Отправка файла оператора: фото — sendPhoto (превью у клиента), остальное — sendDocument."""
    token = integration.secret
    target = chat_id or user_id
    if not token or not target:
        return False
    as_photo = content_type in ("image/jpeg", "image/png") and len(content) <= 10 * 1024 * 1024
    method, field_name = ("sendPhoto", "photo") if as_photo else ("sendDocument", "document")
    try:
        data = request_json_multipart(
            f"{_base(integration)}/bot{token}/{method}",
            fields={"chat_id": target, **({"caption": caption[:1024]} if caption else {})},
            file_field=field_name,
            filename=filename,
            content=content,
            content_type=content_type,
            proxy_url=_proxy(integration),
        )
        return bool(data.get("ok"))
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, json.JSONDecodeError) as error:
        logger.warning("Telegram %s failed for integration %s: %s", method, integration.id, error)
        return False


def download_voice(integration, file_id: str) -> tuple[bytes, str]:
    """Скачивание голосового: getFile -> file_path -> /file/bot<token>/<path>."""
    token = integration.secret
    data = request_json(
        f"{_base(integration)}/bot{token}/getFile?file_id={file_id}",
        proxy_url=_proxy(integration),
    )
    file_path = ((data.get("result") or {}).get("file_path") or "")
    if not data.get("ok") or not file_path:
        raise ValueError(t("conversations.telegram_getfile_failed"))
    content = download_bytes(
        f"{_base(integration)}/file/bot{token}/{file_path}",
        proxy_url=_proxy(integration),
        # Адрес собран из base_url подключения, а его владелец задал сам:
        # у self-hosted Bot API он может быть и внутри сети.
        allowed_host=host_of(_base(integration)),
    )
    suffix = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "oga"
    return content, f"audio/{'ogg' if suffix in ('oga', 'ogg') else suffix}"


def send_voice(integration, *, chat_id: str, user_id: str, content: bytes, content_type: str, duration: int) -> bool:
    """Отправка голосового оператора (sendVoice, multipart)."""
    token = integration.secret
    target = chat_id or user_id
    if not token or not target:
        return False
    suffix = (content_type.rsplit("/", 1)[-1] or "ogg").split(";")[0]
    try:
        data = request_json_multipart(
            f"{_base(integration)}/bot{token}/sendVoice",
            fields={"chat_id": target, **({"duration": str(duration)} if duration else {})},
            file_field="voice",
            filename=f"voice.{suffix}",
            content=content,
            content_type=content_type,
            proxy_url=_proxy(integration),
        )
        return bool(data.get("ok"))
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, json.JSONDecodeError) as error:
        logger.warning("Telegram sendVoice failed for integration %s: %s", integration.id, error)
        return False
