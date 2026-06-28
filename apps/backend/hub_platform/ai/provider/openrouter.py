import http.client
import json
import urllib.error
import urllib.request

from hub_platform.ai.provider.base import ChatMessage, ChatResult, EmbeddingResult, LLMProvider, ProviderError


class OpenRouterProvider(LLMProvider):
    """OpenRouter HTTP adapter (stdlib only). Exercised with a real key; tests use TestProvider."""

    name = "openrouter"

    def __init__(self, *, api_key: str, base_url: str, timeout: float = 30.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        # http.client.HTTPException покрывает IncompleteRead/BadStatusLine (оборванный ответ) —
        # это не OSError, поэтому ловим отдельно, иначе исключение уходит мимо ProviderError.
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, json.JSONDecodeError) as error:
            raise ProviderError(f"{type(error).__name__}: {error}") from error

    def chat(self, *, messages: list[ChatMessage], model: str, params: dict | None = None) -> ChatResult:
        payload = {"model": model, "messages": [{"role": m.role, "content": m.content} for m in messages], **(params or {})}
        data = self._post("/chat/completions", payload)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderError(f"Unexpected OpenRouter response: {error}") from error
        usage = data.get("usage") or {}
        return ChatResult(
            text=text,
            model=data.get("model", model),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
        )

    def embed(self, *, texts: list[str], model: str) -> list[EmbeddingResult]:
        data = self._post("/embeddings", {"model": model, "input": texts})
        try:
            items = data["data"]
        except (KeyError, TypeError) as error:
            raise ProviderError(f"Unexpected OpenRouter response: {error}") from error
        usage = data.get("usage") or {}
        per_text = int(usage.get("prompt_tokens", 0)) // max(1, len(texts))
        return [EmbeddingResult(vector=item["embedding"], model=data.get("model", model), tokens=per_text) for item in items]
