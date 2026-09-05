from chatballs.conversations.transports import email as _email
from chatballs.conversations.transports import max as _max
from chatballs.conversations.transports import telegram as _telegram
from chatballs.integrations.models import IntegrationProvider

_POLL = {
    IntegrationProvider.MAX: _max.poll_updates,
    IntegrationProvider.TELEGRAM: _telegram.poll_updates,
    IntegrationProvider.EMAIL: _email.poll_updates,
}
def _web_noop(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    # Web Chat: ответ уже сохранён в БД, браузер забирает его поллингом — внешней отправки нет.
    return True


_SEND = {
    IntegrationProvider.MAX: _max.send_text,
    IntegrationProvider.TELEGRAM: _telegram.send_text,
    IntegrationProvider.WEB: _web_noop,
    IntegrationProvider.EMAIL: _email.send_text,
}

# Запрос контакта: сообщение с кнопкой «Поделиться контактом» (TG/MAX);
# для Web форму телефона рисует сам виджет по kind=contact_request.
_CONTACT_REQUEST = {
    IntegrationProvider.MAX: _max.send_contact_request,
    IntegrationProvider.TELEGRAM: _telegram.send_contact_request,
    IntegrationProvider.WEB: _web_noop,
    # Email: кнопок нет — просьба уходит обычным письмом.
    IntegrationProvider.EMAIL: _email.send_text,
}

# Подтверждение получения контакта: в TG заодно снимает reply-клавиатуру.
_CONTACT_ACK = {
    IntegrationProvider.MAX: _max.send_text,
    IntegrationProvider.TELEGRAM: _telegram.send_contact_ack,
    IntegrationProvider.WEB: _web_noop,
    IntegrationProvider.EMAIL: _email.send_text,
}

# Приглашение на онлайн-звонок: сообщение с кнопкой-ссылкой /calls/<token>
# (SPEC-HUB-0013 §7.2). Web доставляется поллингом виджета, отправки нет.
_CALL_INVITE = {
    IntegrationProvider.MAX: _max.send_call_invite,
    IntegrationProvider.TELEGRAM: _telegram.send_call_invite,
}

# Провайдеры-мессенджеры, у которых есть транспорт приёма/отправки.
SUPPORTED_PROVIDERS = tuple(_POLL.keys())


def poll(integration):
    return _POLL[integration.provider](integration)


def send_reply(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    return _SEND[integration.provider](integration, chat_id=chat_id, user_id=user_id, text=text)


def send_contact_request(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    return _CONTACT_REQUEST[integration.provider](integration, chat_id=chat_id, user_id=user_id, text=text)


def send_contact_ack(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    return _CONTACT_ACK[integration.provider](integration, chat_id=chat_id, user_id=user_id, text=text)


def send_call_invite(integration, *, chat_id: str, user_id: str, text: str, url: str) -> bool:
    sender = _CALL_INVITE.get(integration.provider)
    if sender is None:
        return False
    return sender(integration, chat_id=chat_id, user_id=user_id, text=text, url=url)


# Голосовые (дизайн-базлайн v2, кадр H): скачивание входящих — TG (file_id) и
# MAX (прямой url) — web-виджет шлёт байты сразу; отправка операторских
# голосовых — Telegram, MAX и Web (доставка поллингом виджета).

def _web_voice_noop(integration, *, chat_id: str, user_id: str, content: bytes, content_type: str, duration: int) -> bool:
    # Web Chat: голосовое уже сохранено в БД, браузер заберёт его поллингом.
    return True


_VOICE_SEND = {
    IntegrationProvider.TELEGRAM: _telegram.send_voice,
    IntegrationProvider.MAX: _max.send_voice,
    IntegrationProvider.WEB: _web_voice_noop,
}


# Файлы и фото: приём — TG (file_id), MAX (url), почта и web-виджет (байты);
# отправка — Telegram (sendDocument/sendPhoto), MAX (/uploads), почта (вложение),
# Web (доставка поллингом виджета).

def _web_file_noop(integration, *, chat_id: str, user_id: str, content: bytes, filename: str, content_type: str, caption: str = "") -> bool:
    return True


_FILE_SEND = {
    IntegrationProvider.TELEGRAM: _telegram.send_file,
    IntegrationProvider.MAX: _max.send_file,
    IntegrationProvider.EMAIL: _email.send_file,
    IntegrationProvider.WEB: _web_file_noop,
}


def download_file(integration, inbound_file) -> tuple[bytes, str]:
    if inbound_file.content:
        return inbound_file.content, inbound_file.content_type or "application/octet-stream"
    if integration.provider == IntegrationProvider.TELEGRAM and inbound_file.file_id:
        content, guessed = _telegram.download_file(integration, inbound_file.file_id)
        return content, inbound_file.content_type or guessed
    if integration.provider == IntegrationProvider.MAX and inbound_file.url:
        return _max.download_file(integration, inbound_file.url, inbound_file.content_type)
    raise ValueError("File download is not supported for this provider")


def supports_file_send(integration) -> bool:
    return integration.provider in _FILE_SEND


def send_file(integration, *, chat_id: str, user_id: str, content: bytes, filename: str, content_type: str, caption: str = "") -> bool:
    sender = _FILE_SEND.get(integration.provider)
    if sender is None:
        return False
    return sender(
        integration,
        chat_id=chat_id,
        user_id=user_id,
        content=content,
        filename=filename,
        content_type=content_type,
        caption=caption,
    )


def download_voice(integration, inbound) -> tuple[bytes, str]:
    if inbound.voice_content:
        return inbound.voice_content, inbound.voice_mime or "audio/webm"
    if integration.provider == IntegrationProvider.TELEGRAM and inbound.voice_file_id:
        return _telegram.download_voice(integration, inbound.voice_file_id)
    if integration.provider == IntegrationProvider.MAX and inbound.voice_url:
        return _max.download_voice(integration, inbound.voice_url)
    raise ValueError("Voice download is not supported for this provider")


def supports_voice_send(integration) -> bool:
    return integration.provider in _VOICE_SEND


def send_voice(integration, *, chat_id: str, user_id: str, content: bytes, content_type: str, duration: int) -> bool:
    sender = _VOICE_SEND.get(integration.provider)
    if sender is None:
        return False
    return sender(
        integration,
        chat_id=chat_id,
        user_id=user_id,
        content=content,
        content_type=content_type,
        duration=duration,
    )
