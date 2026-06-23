from __future__ import annotations

import abc
from dataclasses import dataclass, field


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
