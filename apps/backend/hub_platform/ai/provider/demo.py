"""Демо-провайдер: живой AI без ключей и сети.

Нужен, чтобы человек, развернувший Chatballs за минуту, увидел агента в
работе до подключения BYOK-провайдера. Отвечает детерминированно по знаниям,
которые runtime положил в системные сообщения («Отвечай только на основе этих
знаний»): выбирает предложения с наибольшим пересечением слов с вопросом.
Если знаний по вопросу нет или клиент просит человека — завершает ответ
токеном передачи оператору (HANDOFF_TOKEN), как настоящий провайдер по
протоколу runtime. Явно помечен в UI как демо: качество ответов ограничено.
"""

from __future__ import annotations

import hashlib
import math
import re

from hub_platform.ai.provider.base import ChatMessage, ChatResult, EmbeddingResult, LLMProvider

EMBEDDING_DIM = 16
KNOWLEDGE_MARKER = "Отвечай только на основе этих знаний:"
HANDOFF_TOKEN = "<<HANDOFF>>"
HUMAN_REQUEST_WORDS = ("человек", "оператор", "сотрудник", "менеджер", "живой", "жалоб", "верн", "возврат")
_WORD = re.compile(r"[а-яёa-z0-9]+", re.IGNORECASE)
_HEADER = re.compile(r"^\s*\[[^\]]{1,120}\]\s*")
_STOP = {
    "и", "в", "на", "с", "по", "у", "а", "но", "не", "что", "как", "это", "для", "до", "от",
    "за", "из", "к", "о", "же", "ли", "бы", "вы", "мы", "я", "он", "она", "они", "мне", "вас",
    "есть", "можно", "нужно", "хочу", "подскажите", "здравствуйте", "добрый", "день", "the",
}


def _tokens(text: str) -> set[str]:
    return {
        _stem(word.lower())
        for word in _WORD.findall(text)
        if len(word) > 2 and word.lower() not in _STOP
    }


def _stem(word: str) -> str:
    # Грубая морфология: обрезаем частые русские окончания, чтобы «доставка» ≈ «доставку».
    for suffix in ("ами", "ями", "ого", "его", "ому", "ему", "ыми", "ими", "ах", "ях", "ов", "ев", "ам", "ям", "ой", "ей", "ую", "юю", "ая", "яя", "ые", "ие", "ть", "ся", "а", "я", "ы", "и", "у", "ю", "е", "о"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _count_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _deterministic_vector(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    raw = [float(digest[i % len(digest)]) for i in range(EMBEDDING_DIM)]
    norm = math.sqrt(sum(value * value for value in raw)) or 1.0
    return [value / norm for value in raw]


def _knowledge_sentences(messages: list[ChatMessage]) -> list[str]:
    sentences: list[str] = []
    for message in messages:
        if message.role != "system" or KNOWLEDGE_MARKER not in message.content:
            continue
        body = message.content.split(KNOWLEDGE_MARKER, 1)[1]
        for paragraph in body.split("\n"):
            # Служебный заголовок фрагмента «[Название#N]» и строки markdown-таблиц
            # в ответ клиенту не попадают.
            paragraph = _HEADER.sub("", paragraph).strip(" -•\t")
            if not paragraph or paragraph.startswith("|") or paragraph.startswith("#"):
                continue
            for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
                sentence = sentence.strip()
                if len(sentence) > 15:
                    sentences.append(sentence)
    return sentences


def compose_reply(messages: list[ChatMessage]) -> tuple[str, bool]:
    """Ответ по знаниям и признак передачи оператору."""
    question = next((m.content for m in reversed(messages) if m.role == "user"), "")
    lowered = question.lower()
    wants_human = any(word in lowered for word in HUMAN_REQUEST_WORDS)
    query = _tokens(question)
    scored = []
    for index, sentence in enumerate(_knowledge_sentences(messages)):
        overlap = len(query & _tokens(sentence))
        if overlap:
            scored.append((-overlap, index, sentence))
    scored.sort()
    best = [sentence for _, _, sentence in scored[:2]]
    if best and not wants_human:
        return " ".join(best), False
    if best:
        return (
            " ".join(best)
            + " Передаю диалог сотруднику — он поможет дальше."
        ), True
    return (
        "Уточню этот вопрос у коллег и передам диалог сотруднику — он ответит в рабочее время."
    ), True


class DemoProvider(LLMProvider):
    """Детерминированный провайдер без сети для демо-стенда."""

    name = "demo"

    def chat(self, *, messages: list[ChatMessage], model: str, params: dict | None = None) -> ChatResult:
        text, handoff = compose_reply(messages)
        if handoff:
            text = f"{text}\n{HANDOFF_TOKEN}"
        prompt_tokens = sum(_count_tokens(message.content) for message in messages)
        return ChatResult(
            text=text,
            model=model or "demo",
            prompt_tokens=prompt_tokens,
            completion_tokens=_count_tokens(text),
        )

    def embed(self, *, texts: list[str], model: str) -> list[EmbeddingResult]:
        return [
            EmbeddingResult(vector=_deterministic_vector(text), model=model or "demo", tokens=_count_tokens(text))
            for text in texts
        ]

    def transcribe(self, *, audio: bytes, filename: str, content_type: str, model: str) -> str:
        return "Расшифровка голосовых недоступна в демо-провайдере: подключите OpenRouter или совместимый провайдер в «Настройках»."
