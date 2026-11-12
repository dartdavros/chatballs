from __future__ import annotations

import abc
from dataclasses import dataclass, field

from chatballs.i18n import t


@dataclass(frozen=True)
class ToolSpec:
    """Инструмент, как его видит модель: имя, описание и JSON Schema параметров."""

    name: str
    description: str
    parameters: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCall:
    """Вызов инструмента, запрошенный моделью.

    `id` выдаёт провайдер: результат возвращается сообщением роли `tool` с тем
    же `tool_call_id`, иначе модель не свяжет ответ с вызовом.
    """

    id: str
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    # Текст уже собран с токенами хода (chatballs.ai.pseudonymization) и
    # повторно не маскируется. Только для блоков, которые пишет сам сервер.
    masked: bool = False
    # У сообщения assistant — вызовы, которые запросила модель.
    tool_calls: tuple[ToolCall, ...] = ()
    # У сообщения tool — вызов, на который оно отвечает.
    tool_call_id: str = ""
    # Opaque Responses output, kept only for this in-memory tool loop. It must
    # not be persisted in diagnostics, logged, or sent to Chat Completions.
    response_items: tuple[dict, ...] = field(default=(), repr=False, compare=False)


@dataclass(frozen=True)
class ChatResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    # Непусто — модель не ответила, а запросила инструменты; текст тогда может быть пуст.
    tool_calls: tuple[ToolCall, ...] = ()

    # Preserve reasoning and function-call items for stateless continuation.
    response_items: tuple[dict, ...] = field(default=(), repr=False, compare=False)

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


class ProviderRejected(ProviderError):
    """Отказ, который повтором не лечится: провайдер не принял сам запрос.

    Неверный ключ, несуществующая модель, слишком длинный контекст. Повтор
    потратит ещё один таймаут и получит тот же ответ, а клиент всё это время
    ждёт ответа. «Слишком часто» (429) сюда не относится — это как раз тот
    случай, когда повторить стоит.
    """


class LLMProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def chat(
        self,
        *,
        messages: list[ChatMessage],
        model: str,
        params: dict | None = None,
        tools: list[ToolSpec] | None = None,
    ) -> ChatResult: ...

    def supports_tools(self, *, model: str) -> bool:
        """Умеет ли модель вызывать инструменты (SPEC-0023 R-10).

        Ответ стоит обращения к провайдеру, поэтому спрашивают его через кеш
        (chatballs.ai.tool_support). ProviderError означает «узнать не удалось».
        """
        return False

    @abc.abstractmethod
    def embed(self, *, texts: list[str], model: str) -> list[EmbeddingResult]: ...

    def transcribe(self, *, audio: bytes, filename: str, content_type: str, model: str) -> str:
        """Расшифровка аудио (дизайн-базлайн v2). Реализуется OpenAI-совместимыми
        адаптерами (POST /audio/transcriptions); остальные явно отказывают."""
        raise ProviderError(t("ai.provider_no_transcription", provider=self.name))
