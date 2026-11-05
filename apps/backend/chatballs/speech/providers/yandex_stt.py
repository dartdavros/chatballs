"""SpeechKit STT REST v3: inline content, bounded polling и попытка cleanup."""

import base64
import json
import logging
import re
import time

import httpx

from chatballs.speech.contracts import SPEECHKIT_MODELS
from chatballs.speech.errors import SpeechError
from chatballs.speech.formats import SAMPLE_RATE, normalize_audio
from chatballs.speech.providers.yandex_http import request
from chatballs.speech.providers.yandex_results import transcript

STT_URL = "https://stt.api.cloud.yandex.net/stt/v3/"
OPERATIONS_URL = "https://operation.api.cloud.yandex.net/operations/"
logger = logging.getLogger(__name__)


class YandexSTT:
    def __init__(self, *, api_key: str, folder_id: str, language: str, timeout: float | None = None):
        self.api_key = api_key
        self.folder_id = folder_id
        self.language = language
        self.timeout = min(timeout or 40, 40)

    def transcribe(self, *, audio: bytes, filename: str, content_type: str, model: str) -> str:
        normalized = normalize_audio(audio, max_seconds=300)
        return self.recognize_pcm(normalized.pcm, model=model)

    def recognize_pcm(self, pcm: bytes, *, model: str = "general") -> str:
        if not self.api_key or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.folder_id):
            raise SpeechError("unavailable")
        if model not in SPEECHKIT_MODELS:
            raise SpeechError("model_unsupported")
        if self.language not in {"ru-RU", "en-US"}:
            raise SpeechError("language_unsupported")
        if not pcm or len(pcm) > 10 * 1024 * 1024:
            raise SpeechError("too_large")
        deadline = time.monotonic() + self.timeout
        payload = {
            "content": base64.b64encode(pcm).decode("ascii"),
            "recognitionModel": {
                "model": model,
                "audioFormat": {"rawAudio": {"audioEncoding": "LINEAR16_PCM", "sampleRateHertz": str(SAMPLE_RATE), "audioChannelCount": "1"}},
                "languageRestriction": {"restrictionType": "WHITELIST", "languageCode": [self.language]},
                "textNormalization": {"textNormalization": "TEXT_NORMALIZATION_ENABLED"},
            },
        }
        operation_id = ""
        with httpx.Client(
            headers={"Authorization": f"Api-Key {self.api_key}", "x-folder-id": self.folder_id, "Accept-Encoding": "identity"},
            trust_env=False, follow_redirects=False,
        ) as client:
            try:
                operation = json.loads(request(client, "POST", STT_URL + "recognizeFileAsync", deadline=deadline, json=payload))
                candidate = operation.get("id", "")
                if not isinstance(candidate, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,50}", candidate):
                    raise SpeechError("provider_error")
                operation_id = candidate
                payload.clear()
                while not operation.get("done"):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise SpeechError("timeout")
                    time.sleep(min(1, remaining))
                    operation = json.loads(request(client, "GET", OPERATIONS_URL + operation_id, deadline=deadline))
                if operation.get("error"):
                    raise SpeechError("provider_error")
                return transcript(request(client, "GET", STT_URL + "getRecognition", deadline=deadline, params={"operationId": operation_id}))
            except (ValueError, TypeError, AttributeError):
                raise SpeechError("provider_error") from None
            finally:
                payload.clear()
                if operation_id:
                    try:
                        request(client, "DELETE", STT_URL + "deleteRecognition", deadline=time.monotonic() + 3, params={"operationId": operation_id})
                    except SpeechError:
                        # Не обещаем удаление при неизвестном исходе; никаких payload/id/key.
                        logger.warning("speechkit cleanup outcome unknown")
