"""Native OpenAI BYOK provider: Responses chat, shared embeddings and audio."""

from chatballs.ai.provider.custom import CustomProvider
from chatballs.integrations.openai_urls import DEFAULT_OPENAI_BASE_URL


class OpenAIProvider(CustomProvider):
    name = "openai"

    def __init__(self, *, api_key: str, base_url: str = DEFAULT_OPENAI_BASE_URL,
                 timeout: float = 30.0, proxy_url: str = ""):
        super().__init__(api_key=api_key, base_url=base_url or DEFAULT_OPENAI_BASE_URL,
                         timeout=timeout, proxy_url=proxy_url)

    def _uses_responses(self, model: str) -> bool:
        return True
