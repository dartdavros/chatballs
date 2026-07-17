from hub_platform.ai.provider import openai_http
from hub_platform.ai.provider.base import ChatMessage, ChatResult, EmbeddingResult, LLMProvider


class OpenRouterProvider(LLMProvider):
    """OpenRouter HTTP adapter (stdlib only).

    OpenAI Chat Completions shape with usage.include=true (returns the actual
    USD cost in usage.cost). Delegates HTTP/parsing to the shared openai_http
    layer (ADR-HUB-0033 §7, ADR-HUB-0034 §3); this adapter only carries the
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
