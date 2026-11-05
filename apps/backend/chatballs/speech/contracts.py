"""Каталог способностей адаптеров; SpeechKit не является LLMProvider."""

from dataclasses import dataclass
from typing import Protocol

MAX_RECORDING_BYTES = 10 * 1024 * 1024
MAX_DICTATION_SECONDS = 60
SPEECHKIT_MODELS = ("general", "general:rc", "general:deprecated")
BROWSER_FORMATS = ("audio/webm", "audio/ogg", "audio/mp4")


class Transcriber(Protocol):
    def transcribe(self, *, audio: bytes, filename: str, content_type: str, model: str) -> str: ...


@dataclass(frozen=True, slots=True)
class SpeechCapabilities:
    stt: bool = False
    default_model: str = ""
    models: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    formats: tuple[str, ...] = BROWSER_FORMATS
    max_bytes: int = MAX_RECORDING_BYTES
    max_seconds: int = MAX_DICTATION_SECONDS
    tts: bool = False
    tts_models: tuple[str, ...] = ()
    voices: tuple[dict, ...] = ()


def capabilities(provider: str) -> SpeechCapabilities:
    if provider == "YANDEX_SPEECHKIT":
        from chatballs.speech.tts_contract import TTS_MODELS, VOICES

        return SpeechCapabilities(True, "general", SPEECHKIT_MODELS, ("ru-RU", "en-US"),
                                  tts=True, tts_models=TTS_MODELS,
                                  voices=tuple({"id": voice, "language": language} for voice, language in VOICES.items()))
    if provider in {"OPENROUTER", "CUSTOM"}:
        # Прежний совместимый /audio/transcriptions, список моделей задаёт сервис.
        return SpeechCapabilities(True, "whisper-1")
    return SpeechCapabilities()
