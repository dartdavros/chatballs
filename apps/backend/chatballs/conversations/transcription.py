"""Расшифровка голосовых сообщений через BYOK-провайдера организации.

Три шага (``prepare`` → ``run`` → ``store``) вместо одной функции: обращение к
провайдеру ждёт ответа десятки секунд, и всё это время транзакция занимала бы
соединение из пула (chatballs.tenancy.middleware). Кто может разнести шаги —
разносит: ход AI (chatballs.conversations.ai_turn) и кнопка «расшифровать» в
рабочем месте (chatballs.conversations.voice_views).
"""

from __future__ import annotations

from dataclasses import dataclass

from chatballs.ai.provider.base import ProviderError
from chatballs.conversations.models import Message, TranscriptStatus


@dataclass(frozen=True, slots=True)
class TranscriptionJob:
    """Всё, что нужно провайдеру, — уже прочитанное из базы и хранилища.

    Разложено на три шага (``prepare`` → ``run`` → ``store``), чтобы вызывающий
    мог держать транзакцию только вокруг первого и третьего: обращение к
    провайдеру ждёт ответа десятки секунд, и всё это время транзакция занимала
    бы соединение из пула (chatballs.tenancy.middleware).
    """

    provider: object
    model: str
    audio: bytes
    filename: str
    content_type: str


def prepare_transcription(channel, message: Message) -> TranscriptionJob | None:
    """Шаг в транзакции: провайдер организации, модель и байты аудио."""
    from chatballs.ai.provider.factory import get_transcription_provider
    from chatballs.ai.provider.routing import (
        DEFAULT_TRANSCRIPTION_MODEL,
        resolve_transcription_model,
    )

    if getattr(channel, "ai_agent", None) is None:
        from chatballs.i18n import t

        raise ProviderError(t("ai.agent_without_llm_integration"))
    if not message.audio:
        return None
    provider = get_transcription_provider(channel=channel)
    try:
        model = resolve_transcription_model(channel)
    except ProviderError:
        from django.conf import settings

        if settings.CHATBALLS_AI_PROVIDER != "test":
            raise
        model = DEFAULT_TRANSCRIPTION_MODEL  # Явная штатная тестовая поверхность.
    with message.audio.open("rb") as handle:
        audio = handle.read()
    return TranscriptionJob(
        provider=provider,
        model=model,
        audio=audio,
        filename=message.audio.name.rsplit("/", 1)[-1],
        content_type=message.audio_content_type or "audio/ogg",
    )


def run_transcription(job: TranscriptionJob) -> str:
    """Шаг без транзакции: обращение к провайдеру."""
    return job.provider.transcribe(
        audio=job.audio,
        filename=job.filename,
        content_type=job.content_type,
        model=job.model,
    ).strip()


def store_transcription(message: Message, transcript: str) -> None:
    """Шаг в транзакции: сохранить стенограмму и статус."""
    message.transcript = transcript
    message.transcript_status = TranscriptStatus.READY if transcript else TranscriptStatus.FAILED
    message.save(update_fields=["transcript", "transcript_status"])


def mark_transcription_failed(message: Message) -> None:
    """Статус FAILED — оператор повторит кнопкой."""
    message.transcript_status = TranscriptStatus.FAILED
    message.save(update_fields=["transcript_status"])
