"""Custom BYOK: preserve Chat Completions compatibility and support Responses."""

from chatballs.ai.provider import openai_responses, openai_tools
from chatballs.ai.provider.base import ChatMessage, ChatResult, ProviderRejected, ToolSpec
from chatballs.ai.provider.openrouter import OpenRouterProvider
from chatballs.integrations.openai_urls import is_gpt6, normalize_base_url, uses_responses


class CustomProvider(OpenRouterProvider):
    """Use Responses for direct OpenAI GPT-6 or an explicit /responses URL.

    Other custom servers and older models retain their existing Chat Completions
    protocol. Embeddings and transcription still use the normalized API root.
    """

    name = "custom"

    def __init__(self, *, api_key: str, base_url: str, timeout: float = 30.0,
                 proxy_url: str = ""):
        self._configured_base_url = base_url
        super().__init__(api_key=api_key, base_url=normalize_base_url(base_url),
                         timeout=timeout, proxy_url=proxy_url)

    def _uses_responses(self, model: str) -> bool:
        return uses_responses(self._configured_base_url, model)

    def chat(self, *, messages: list[ChatMessage], model: str, params: dict | None = None,
             tools: list[ToolSpec] | None = None) -> ChatResult:
        if not self._uses_responses(model):
            return super().chat(messages=messages, model=model, params=params, tools=tools)
        return openai_responses.responses(
            base_url=self.base_url, api_key=self.api_key, messages=messages, model=model,
            timeout=self.timeout, proxy_url=self.proxy_url, params=params, tools=tools,
        )

    def supports_tools(self, *, model: str) -> bool:
        if not self._uses_responses(model):
            return self._probe_tools(model=model)
        # 64 Chat Completions tokens are insufficient for reasoning models.
        # An incomplete response propagates as ProviderError (unknown), not a
        # false capability cached for 24 hours.
        params = {"tool_choice": {"type": "function", "name": openai_tools.PROBE_TOOL.name},
                  "max_output_tokens": 4096}
        if is_gpt6(model):
            params["reasoning"] = {"effort": "low"}
        try:
            result = self.chat(messages=openai_tools.PROBE_MESSAGES, model=model,
                               params=params, tools=[openai_tools.PROBE_TOOL])
        except ProviderRejected:
            return False
        return any(call.name == openai_tools.PROBE_TOOL.name for call in result.tool_calls)
