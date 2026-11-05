"""Explicit SpeechKit TTS catalog; no inherited provider or voice."""

import re
from functools import lru_cache

from chatballs.speech.errors import SpeechError

TTS_MODELS = ("", "general")
# Official catalog: https://aistudio.yandex.ru/en/docs/speechkit/tts/voices
# This catalog contains general voices; LiveTTS requires a different family.
VOICES = {"alena": "ru-RU", "filipp": "ru-RU", "ermil": "ru-RU", "jane": "ru-RU",
          "omazh": "ru-RU", "zahar": "ru-RU", "john": "en-US"}


@lru_cache(maxsize=1)
def language_factory():
    from langdetect.detector_factory import PROFILES_DIRECTORY, DetectorFactory

    # Publish only a fully loaded factory; each request creates its own detector.
    factory = DetectorFactory()
    factory.seed = 0
    factory.load_profile(PROFILES_DIRECTORY)
    return factory


def validate_selection(model: str, voice: str) -> None:
    if model not in TTS_MODELS:
        raise SpeechError("tts_model_unsupported")
    if voice and voice not in VOICES:
        raise SpeechError("voice_unavailable")


def validate_language(text: str, voice: str) -> None:
    if voice not in VOICES:
        raise SpeechError("voice_unavailable")
    letters = "".join(character for character in text if character.isalpha())
    expected = VOICES[voice].split("-")[0]
    if expected == "en" and re.search(r"[А-Яа-яЁё]", letters):
        raise SpeechError("voice_language_unsupported")
    if expected == "ru" and letters and not re.search(r"[А-Яа-яЁё]", letters):
        raise SpeechError("voice_language_unsupported")
    if not letters:
        return
    from langdetect import LangDetectException

    try:
        detector = language_factory().create()
        detector.append(text)
        language = detector.detect()
    except LangDetectException:
        raise SpeechError("voice_language_unsupported") from None
    if language != expected:
        raise SpeechError("voice_language_unsupported")
