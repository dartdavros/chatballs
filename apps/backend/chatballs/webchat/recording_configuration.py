"""WEB хранит режим и лимиты; остальные каналы используют прежние настройки."""

from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.speech.contracts import MAX_DICTATION_SECONDS, MAX_RECORDING_BYTES
from chatballs.speech.errors import SpeechError

MODES = {"off", "voice_message", "dictation"}


def recording_settings(integration) -> dict:
    stored = integration.config
    return {
        "microphoneMode": stored.get("microphoneMode", "voice_message" if integration.voice_messages_enabled else "off"),
        "maxRecordingBytes": stored.get("maxRecordingBytes", MAX_RECORDING_BYTES),
        "maxDictationSeconds": stored.get("maxDictationSeconds", MAX_DICTATION_SECONDS),
        "answerPlaybackEnabled": stored.get("answerPlaybackEnabled", False),
    }


def normalize_recording(config: dict, previous: dict) -> dict:
    result = {}
    playback = config.get("answerPlaybackEnabled", previous.get("answerPlaybackEnabled", False))
    if type(playback) is not bool:
        raise ValidationError({"answerPlaybackEnabled": t("api.boolean_required")})
    result["answerPlaybackEnabled"] = playback
    for key, default, limit in (
        ("maxRecordingBytes", MAX_RECORDING_BYTES, MAX_RECORDING_BYTES),
        ("maxDictationSeconds", MAX_DICTATION_SECONDS, MAX_DICTATION_SECONDS),
    ):
        value = config.get(key, previous.get(key, default))
        if type(value) is not int or not 1 <= value <= limit:
            raise ValidationError({key: t("speech.limits_invalid")})
        result[key] = value
    mode = config.get("microphoneMode", previous.get("microphoneMode"))
    if mode is not None:
        if not isinstance(mode, str) or mode not in MODES:
            raise ValidationError({"microphoneMode": t("speech.mode_invalid")})
        result["microphoneMode"] = mode
    return result


def public_recording(integration) -> dict:
    result = recording_settings(integration)
    available = result["microphoneMode"] != "off"
    if result["microphoneMode"] == "dictation":
        from chatballs.speech.routing import resolve_model

        try:
            resolve_model(integration.channel)
        except SpeechError:
            available = False
    return {**result, "available": available}
