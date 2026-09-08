from chatballs.ai.provider import openai_http
from chatballs.ai.provider.base import ChatMessage, ChatResult, EmbeddingResult, LLMProvider


class OpenRouterProvider(LLMProvider):
    """OpenRouter HTTP adapter (stdlib only).

    OpenAI Chat Completions shape with usage.include=true (returns the actual
    USD cost in usage.cost). Delegates HTTP/parsing to the shared openai_http
    layer (ADR-HUB-0033 §7, ADR-CHATBALLS-0034 §3); this adapter only carries the
    OpenRouter product semantics (cost reporting). Exercised with a real key;
    tests use the LocalProvider.
    """

    name = "openrouter"

    def __init__(self, *, api_key: str, base_url: str, timeout: float = 30.0, proxy_url: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.proxy_url = proxy_url or ""

    def chat(self, *, messages: list[ChatMessage], model: str, params: dict | None = None) -> ChatResult:
        # usage.include=true — OpenRouter возвращает фактическую стоимость в usage.cost (USD).
        return openai_http.chat_completions(
            base_url=self.base_url, api_key=self.api_key, messages=messages, model=model,
            timeout=self.timeout, proxy_url=self.proxy_url, params=params, include_cost=True,
        )

    def embed(self, *, texts: list[str], model: str) -> list[EmbeddingResult]:
        return openai_http.embeddings(
            base_url=self.base_url, api_key=self.api_key, texts=texts, model=model,
            timeout=self.timeout, proxy_url=self.proxy_url,
        )

    def transcribe(self, *, audio: bytes, filename: str, content_type: str, model: str) -> str:
        # OpenAI-совместимый POST /audio/transcriptions (whisper). Формат ответа
        # {"text": "..."}; ошибки транслируются в ProviderError.
        import json
        import urllib.error
        import urllib.request

        from chatballs.ai.provider.base import ProviderError
        from chatballs.conversations.transports.base import multipart_body
        from chatballs.integrations.proxy import build_opener

        body, body_type = multipart_body(
            {"model": model},
            file_field="file",
            filename=filename,
            content=audio,
            content_type=content_type,
        )
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": body_type,
            },
            method="POST",
        )
        try:
            with build_opener(self.proxy_url).open(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:300]
            raise ProviderError(f"Расшифровка не удалась: HTTP {error.code} {detail}") from error
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise ProviderError(f"Расшифровка не удалась: {error}") from error
        text = str(payload.get("text") or "").strip()
        if not text:
            raise ProviderError("Провайдер вернул пустую расшифровку")
        return text
