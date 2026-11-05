"""Bounded sequential SpeechKit v3 synthesis; PCM joins into one WAV in memory."""

import base64
import binascii
import io
import json
import time
import wave

import httpx

from chatballs.speech.errors import SpeechError
from chatballs.speech.providers.yandex_http import request
from chatballs.speech.tts_contract import validate_selection

TTS_URL = "https://tts.api.cloud.yandex.net/tts/v3/utteranceSynthesis"
MAX_TEXT = 100_000
MAX_AUDIO = 64 * 1024 * 1024
SAMPLE_RATE = 22050


def decode_segment(raw: bytes, remaining: int) -> bytes:
    segment = bytearray()
    try:
        for line in raw.splitlines():
            record = json.loads(line)
            result = record.get("result", record)
            if "error" in record or "error" in result:
                raise ValueError
            data = result.get("audioChunk", {}).get("data", "")
            segment.extend(base64.b64decode(data, validate=True))
            if len(segment) > remaining:
                raise SpeechError("tts_text_limit")
    except (ValueError, TypeError, AttributeError, binascii.Error):
        raise SpeechError("tts_provider_error") from None
    if not segment or len(segment) % 2:
        raise SpeechError("tts_provider_error")
    return bytes(segment)


def text_parts(text: str, limit: int = 1000):
    """Preserve every character and its order, preferring word boundaries.

    v3 unsafeMode supports up to 5000 characters. Use 1000 per request to
    bound response memory; unsafeMode also removes the 24-second phrase cap.
    """
    while text:
        end = min(len(text), limit)
        if end < len(text):
            boundary = max(text.rfind(" ", 0, end), text.rfind("\n", 0, end))
            if boundary > end // 2:
                end = boundary + 1
        yield text[:end]
        text = text[end:]


class YandexTTS:
    def __init__(self, *, api_key: str, folder_id: str, model: str, voice: str):
        self.api_key, self.folder_id = api_key, folder_id
        self.model, self.voice = model, voice

    def synthesize(self, text: str) -> bytes:
        validate_selection(self.model, self.voice)
        if not self.voice or not self.api_key:
            raise SpeechError("tts_unavailable")
        if not text.strip() or len(text) > MAX_TEXT:
            raise SpeechError("tts_text_limit")
        deadline = time.monotonic() + 180
        pcm = bytearray()
        with httpx.Client(headers={"Authorization": f"Api-Key {self.api_key}",
                                   "x-folder-id": self.folder_id, "Accept-Encoding": "identity"},
                          trust_env=False, follow_redirects=False) as client:
            for part in text_parts(text):
                payload = {"text": part, "hints": [{"voice": self.voice}], "unsafeMode": True,
                           "outputAudioSpec": {"rawAudio": {"audioEncoding": "LINEAR16_PCM", "sampleRateHertz": str(SAMPLE_RATE)}}}
                if self.model:
                    payload["model"] = self.model
                raw = request(client, "POST", TTS_URL, deadline=deadline, json=payload, max_response_bytes=16 * 1024 * 1024)
                payload.clear()
                pcm.extend(decode_segment(raw, MAX_AUDIO - len(pcm)))
        with io.BytesIO() as output:
            with wave.open(output, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(SAMPLE_RATE)
                wav.writeframes(pcm)
            return output.getvalue()
