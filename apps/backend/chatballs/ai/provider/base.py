from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class ChatResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    # Фактическая стоимость, сообщённая провайдером (micro-USD). 0 — провайдер не
    # вернул цену, тогда считаем по прайс-таблице (ai/pricing.py).
    cost_micros: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    model: str
    tokens: int = 0


class ProviderError(Exception):
    """Transient/technical provider failure (eligible for retry / circuit breaker)."""


class LLMProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def chat(self, *, messages: list[ChatMessage], model: str, params: dict | None = None) -> ChatResult: ...

    @abc.abstractmethod
    def embed(self, *, texts: list[str], model: str) -> list[EmbeddingResult]: ...

    def transcribe(self, *, audio: bytes, filename: str, content_type: str, model: str) -> str:
        """Расшифровка аудио (дизайн-базлайн v2). Реализуется OpenAI-совместимыми
        адаптерами (POST /audio/transcriptions); остальные явно отказывают."""
        raise ProviderError(f"Провайдер {self.name} не поддерживает расшифровку аудио")
