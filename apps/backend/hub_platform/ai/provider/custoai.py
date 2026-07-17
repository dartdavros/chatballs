from hub_platform.ai.provider import openai_http
from hub_platform.ai.provider.base import (
    ChatMessage,
    ChatResult,
    EmbeddingResult,
    LLMProvider,
    ProviderError,
)


class CustoAIProvider(LLMProvider):
    """Managed CustoAI adapter backed by the platform credential.

    Yandex AI Studio is intentionally hidden behind the product-level CustoAI
    name. Its API is OpenAI-compatible, so transport and response parsing stay
    in the shared HTTP layer rather than a Yandex-specific adapter.
    """

    name = "custoai"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

    def chat(
        self, *, messages: list[ChatMessage], model: str, params: dict | None = None
    ) -> ChatResult:
        result = openai_http.chat_completions(
            base_url=self.base_url,
            api_key=self.api_key,
            messages=messages,
            model=self.model,
            timeout=self.timeout,
            params=params,
            include_cost=False,
        )
        if result.total_tokens <= 0:
            raise ProviderError("CustoAI response does not contain token usage")
        return result

    def embed(self, *, texts: list[str], model: str) -> list[EmbeddingResult]:
        return openai_http.embeddings(
            base_url=self.base_url,
            api_key=self.api_key,
            texts=texts,
            model=model,
            timeout=self.timeout,
        )
