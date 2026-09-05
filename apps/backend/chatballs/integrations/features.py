"""Функции точки входа: что разрешено клиенту и оператору в диалогах через
эту интеграцию — голосовые сообщения и онлайн-звонки (аудио/видео).

Звонки технически возможны там, где есть доставка приглашения: Telegram, MAX
(кнопка-ссылка) и Web-виджет (баннер в виджете). Почта звонки не поддерживает.
"""

from __future__ import annotations

from chatballs.integrations.models import Integration, IntegrationProvider

CALL_PROVIDERS = (IntegrationProvider.TELEGRAM, IntegrationProvider.MAX, IntegrationProvider.WEB)


def supports_calls(integration: Integration | None) -> bool:
    return integration is not None and integration.provider in CALL_PROVIDERS


def voice_messages_allowed(integration: Integration | None) -> bool:
    return integration is not None and integration.voice_messages_enabled


def call_allowed(integration: Integration | None, kind: str) -> bool:
    if not supports_calls(integration):
        return False
    return integration.video_calls_enabled if kind == "VIDEO" else integration.audio_calls_enabled


def features_payload(integration: Integration | None) -> dict[str, bool]:
    return {
        "voiceMessages": voice_messages_allowed(integration),
        "audioCalls": call_allowed(integration, "AUDIO"),
        "videoCalls": call_allowed(integration, "VIDEO"),
    }
