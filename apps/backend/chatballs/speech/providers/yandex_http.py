"""Фиксированные HTTPS endpoints, ограниченные ответы и общий deadline."""

import time

import httpx

from chatballs.speech.errors import SpeechError

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


def request(client: httpx.Client, method: str, url: str, *, deadline: float, max_response_bytes=MAX_RESPONSE_BYTES, **kwargs) -> bytes:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise SpeechError("timeout")
    try:
        with client.stream(method, url, timeout=min(10, remaining), **kwargs) as response:
            if response.status_code in {401, 403}:
                raise SpeechError("access_denied")
            if not response.is_success:
                raise SpeechError("provider_error")
            content = bytearray()
            for chunk in response.iter_raw(chunk_size=65536):
                if time.monotonic() >= deadline:
                    raise SpeechError("timeout")
                if len(content) + len(chunk) > max_response_bytes:
                    raise SpeechError("provider_error")
                content.extend(chunk)
            return bytes(content)
    except httpx.TimeoutException:
        raise SpeechError("timeout") from None
    except httpx.HTTPError:
        raise SpeechError("provider_error") from None
