"""Ход агента по шагам: транзакция — сеть — транзакция — сеть — транзакция.

Ответ клиенту складывается из двух обращений к провайдеру (вектор вопроса и
сам ответ) и нескольких обращений к базе между ними. Сделанные подряд, они
держат транзакцию организации открытой всё время ожидания провайдера — а это
минуты (chatballs.ai.invocation). Здесь работа разложена так, чтобы каждое
обращение к базе шло своей короткой транзакцией, а походы наружу оставались
между ними.

Порядок шагов у вызывающего (chatballs.conversations.ai_turn):

1. в транзакции: `plan_query_embedding`
2. вне транзакции: `run_query_embedding`
3. в транзакции: `plan_chat`
4. вне транзакции: `run_turn_chat`
5. в транзакции: `record_turn` и запись ответа

Если агенту включены инструменты, шаг 4 — цикл «модель → вызовы → результаты
→ модель» (chatballs.ai.tool_loop): по-прежнему вне транзакции.

Шаги `run_*` ошибок провайдера не поднимают: отказ — это такой же результат
хода, его пишут в журнал и разбирают в диалоге (передачей оператору).

Провайдер получает тексты с токенами вместо персональных значений (SPEC-0022).
Карта хода (`turn_pseudonymizer`) одна на вопрос для вектора и на запрос к
модели; она едет через план хода в памяти, и `record_turn` по ней возвращает
значения в ответ. В базу, журнал вызовов и события карта не попадает.
"""

from __future__ import annotations

import time
from dataclasses import replace

from django.conf import settings

from chatballs.ai.diagnostic_snapshot import diagnostic_context
from chatballs.ai.invocation import (
    EmbeddingJob,
    prepare_chat,
    prepare_embedding,
    record_chat,
    record_embedding,
    restore_reply,
    run_chat,
    run_embedding,
)
from chatballs.ai.models import AIAgent
from chatballs.ai.provider.base import (
    ChatMessage,
    ProviderError,
)
from chatballs.ai.pseudonymization import Pseudonymizer, contact_known_values
from chatballs.ai.retrieval import merge_hits
from chatballs.ai.runtime import build_turn_messages
from chatballs.ai.site_context import client_context_prompt, masked_field_values
from chatballs.ai.tool_loop import ChatRound, run_tool_loop, with_tools
from chatballs.ai.turn_skills import plan_turn_skills
from chatballs.ai.turn_tools import plan_turn_tools
from chatballs.ai.turn_types import QueryEmbedding, TurnAnswer, TurnPlan
from chatballs.conversations.models import Conversation
from chatballs.i18n import customer_language
from chatballs.integrations.http_tool import ClientData

FRAGMENT_LIMIT = 5


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)



def turn_pseudonymizer(conversation: Conversation | None) -> Pseudonymizer:
    """Карта хода: известные значения — имя, e-mail и телефон контакта диалога
    и его свои поля сайта в режиме «под маской»."""

    contact = getattr(conversation, "contact", None)
    if contact is None:
        return Pseudonymizer()
    return Pseudonymizer([
        *contact_known_values(name=contact.name, email=contact.email, phone=contact.phone),
        *masked_field_values(conversation),
    ])


def plan_query_embedding(
    *, agent: AIAgent, query: str, pseudonymizer: Pseudonymizer
) -> EmbeddingJob | None:
    """Шаг в транзакции: чем считать вектор вопроса. None — считать нечем.

    Вопрос уходит в модель эмбеддингов под маской той же карты хода.
    """
    if not query.strip():
        return None
    try:
        return prepare_embedding(
            channel=agent.channel,
            texts=[query],
            model=settings.CHATBALLS_AI_EMBEDDING_MODEL,
            timeout=settings.CHATBALLS_AI_TURN_TIMEOUT,
            pseudonymizer=pseudonymizer,
        )
    except ProviderError:
        # Провайдера нет или он не настроен: семантический поиск необязателен.
        return None


def run_query_embedding(job: EmbeddingJob | None) -> QueryEmbedding:
    """Шаг без транзакции: обращение к провайдеру за вектором."""

    if job is None:
        return QueryEmbedding()
    started = time.monotonic()
    try:
        results = run_embedding(job)
    except ProviderError:
        # Знания найдутся лексическим поиском; ход из-за этого не срывается.
        return QueryEmbedding(latency_ms=_elapsed_ms(started))
    return QueryEmbedding(
        vector=results[0].vector if results else None,
        model=job.model,
        latency_ms=_elapsed_ms(started),
        results=results,
    )


def plan_chat(
    *,
    agent: AIAgent,
    message: str,
    history: list[dict] | None = None,
    embedding: QueryEmbedding | None = None,
    style_guard: bool = True,
    conversation: Conversation | None = None,
    pseudonymizer: Pseudonymizer | None = None,
    client: ClientData | None = None,
    client_context: list[tuple[str, str]] | None = None,
    test_tenant=None,
    action_preview: bool = True,
    action_turn_id=None,
    site_event_launch_id=None,
) -> TurnPlan:
    """Шаг в транзакции: поиск знаний, сборка промпта, выбор модели и инструментов.

    Заодно здесь оседает журнальная строка о векторе вопроса: считали его
    снаружи транзакции, а писать её всё равно в базу.

    Карту хода передают ту же, что маскировала вопрос для вектора; без неё
    она собирается из контакта диалога. Данные клиента для привязанных
    параметров инструментов (`client`) по умолчанию тоже берутся из диалога.
    """
    if pseudonymizer is None:
        pseudonymizer = turn_pseudonymizer(conversation)
    embedding = embedding or QueryEmbedding()
    if embedding.results:
        record_embedding(
            channel=agent.channel,
            model=embedding.model,
            purpose="retrieval_query",
            results=embedding.results,
            latency_ms=embedding.latency_ms,
        )
    fragments = merge_hits(agent, message, embedding.vector, limit=FRAGMENT_LIMIT)
    job = prepare_chat(
        channel=agent.channel,
        messages=build_turn_messages(
            agent=agent,
            message=message,
            history=history,
            fragments=fragments,
            style_guard=style_guard,
            conversation=conversation,
            pseudonymizer=pseudonymizer,
        ),
        pseudonymizer=pseudonymizer,
        model=agent.model,
        params=agent.model_params or None,
        timeout=settings.CHATBALLS_AI_TURN_TIMEOUT,
    )
    if client_context:
        # Контекст маскируется той же картой, затем экранируется построчно.
        # Готовые системные токены повторно маскировать нельзя.
        messages = list(job.messages)
        position = next((i for i, item in enumerate(messages) if item.role != "system"), len(messages))
        messages.insert(position, ChatMessage(
            role="system", content=client_context_prompt(client_context, pseudonymizer), masked=True,
        ))
        job = replace(job, messages=messages)
    client, redactor, snapshot = diagnostic_context(agent, conversation, pseudonymizer, client)
    tools = plan_turn_tools(agent=agent, conversation=conversation, client=client,
                           decisions=snapshot["toolAvailability"])
    from chatballs.integrations.execution.ai_bridge import plan_actions
    tools.extend(plan_actions(agent, conversation, preview=action_preview if test_tenant else False,
                              test_tenant=test_tenant, test_client=client, turn_id=action_turn_id,
                              reserved_names=[tool.spec.name for tool in tools], site_event_launch_id=site_event_launch_id))
    from chatballs.integrations.execution.ai_context import action_context
    action_data = action_context(agent, conversation, pseudonymizer)
    if action_data:
        job = replace(job, messages=[ChatMessage(role="system", content=action_data, masked=True), *job.messages])
    skills = plan_turn_skills(agent, tools, pseudonymizer)
    return TurnPlan(
        job=with_tools(job, tools, pseudonymizer, skills),
        skills=skills,
        fragment_ids=[fragment.id for fragment in fragments],
        pseudonymizer=pseudonymizer,
        tools=tools,
        diagnostic_snapshot=snapshot,
        diagnostic_redactor=redactor,
        language=customer_language(agent.organization),
    )


def run_turn_chat(plan: TurnPlan, *, time_left: float | None = None) -> TurnAnswer:
    """Шаг без транзакции: обращение к модели за ответом.

    С инструментами это цикл из нескольких обращений (chatballs.ai.tool_loop);
    `time_left` — сколько секунд осталось до срока хода.
    """
    started = time.monotonic()
    if plan.tools or plan.skills.enabled:
        loop = run_tool_loop(plan.job, plan.tools, plan.pseudonymizer,
                             time_left=time_left, skills=plan.skills, language=plan.language)
        last = loop.rounds[-1]
        return TurnAnswer(
            result=None if last.error else last.result,
            error=last.error,
            latency_ms=_elapsed_ms(started),
            rounds=loop.rounds,
            tool_calls=loop.tool_calls,
            requests=loop.requests,
            prepared_reply=loop.prepared_reply if not last.error else None,
        )
    try:
        job = replace(plan.job, deadline=started + time_left) if time_left is not None else plan.job
        result = run_chat(job)
    except ProviderError as error:
        return TurnAnswer(error=error, latency_ms=_elapsed_ms(started))
    if job.deadline is not None and time.monotonic() >= job.deadline:
        error = ProviderError("turn deadline passed")
        return TurnAnswer(error=error, rounds=(ChatRound(result=result, error=error),), requests=(job,))
    return TurnAnswer(result=result, latency_ms=_elapsed_ms(started))


def record_turn(*, agent: AIAgent, plan: TurnPlan, answer: TurnAnswer) -> str:
    """Шаг в транзакции: строка журнала вызовов — и об ответе, и об отказе.

    Возвращает ответ модели с настоящими значениями вместо токенов хода: его
    сохраняют в диалог и отправляют клиенту. При отказе — пустая строка.

    У хода с инструментами строк столько, сколько было обращений к модели:
    токены каждого раунда идут в учёт (SPEC-0023 R-15).
    """
    rounds = answer.rounds or (
        ChatRound(result=answer.result, error=answer.error, latency_ms=answer.latency_ms),
    )
    for number, item in enumerate(rounds, start=1):
        record_chat(
            channel=agent.channel,
            job=plan.job,
            purpose="agent_chat",
            result=item.result,
            error=item.error,
            latency_ms=item.latency_ms,
            # Знания относятся к ходу, а не к раунду: их несёт последняя строка.
            used_fragment_ids=plan.fragment_ids if number == len(rounds) else None,
        )
    if answer.result is None:
        return ""
    if answer.prepared_reply is not None:
        return answer.prepared_reply.text
    return restore_reply(
        channel=agent.channel, pseudonymizer=plan.pseudonymizer, text=answer.result.text
    )
