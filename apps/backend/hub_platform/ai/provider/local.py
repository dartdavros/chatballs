import hashlib
import math

from hub_platform.ai.provider.base import ChatMessage, ChatResult, EmbeddingResult, LLMProvider

# Размерность согласуется со слайсом 3 (pgvector); для тестового провайдера фиксирована.
EMBEDDING_DIM = 16


def _count_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _deterministic_vector(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    raw = [float(digest[i % len(digest)]) for i in range(EMBEDDING_DIM)]
    norm = math.sqrt(sum(value * value for value in raw)) or 1.0
    return [value / norm for value in raw]


class LocalProvider(LLMProvider):
    """Deterministic, network-free provider for local development and tests."""

    name = "test"

    def chat(self, *, messages: list[ChatMessage], model: str, params: dict | None = None) -> ChatResult:
        last_user = next((message.content for message in reversed(messages) if message.role == "user"), "")
        text = f"[test:{model}] " + (last_user[:200] if last_user else "ok")
        prompt_tokens = sum(_count_tokens(message.content) for message in messages)
        return ChatResult(
            text=text,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=_count_tokens(text),
        )

    def embed(self, *, texts: list[str], model: str) -> list[EmbeddingResult]:
        return [
            EmbeddingResult(vector=_deterministic_vector(text), model=model, tokens=_count_tokens(text))
            for text in texts
        ]
