from hub_platform.ai.provider.openrouter import OpenRouterProvider


class CustomProvider(OpenRouterProvider):
    """Generic OpenAI-compatible BYOK adapter (ADR-HUB-0034).

    Reuses the OpenRouter HTTP layer verbatim: the contract is identical
    (POST /chat/completions, POST /embeddings, Authorization: Bearer <key>,
    response with choices[0].message.content and usage). The only difference
    from OpenRouter is the absence of a model catalog — the model identifier
    is supplied by the integration owner as free text and read at runtime
    (ADR-HUB-0034 §4). The distinct name lets routing and accounting tell the
    two BYOK modes apart.
    """

    name = "custom"
