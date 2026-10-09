"""Ход AI по входящему сообщению — отдельная работа, а не часть приёма.

Раньше ответ считался прямо в приёме: цикл опроса мессенджеров и HTTP-запрос
виджета ждали провайдера минутами, держа открытой транзакцию организации, — и
всё это время ни одно другое входящее не забиралось. Теперь приём доводит дело
до записи сообщения и ставит ход в очередь событий, а считает его роль событий
(`run_worker --role=events`), которую можно держать в нескольких процессах.

Границы транзакций здесь и есть главное: каждое обращение к базе идёт своей
короткой транзакцией, походы к провайдеру и в мессенджер остаются между ними.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from chatballs.ai.diagnostic_capture import (
    finish_diagnostic,
    record_planning_failure,
    start_diagnostic,
)
from chatballs.ai.models import HISTORY_LIMIT_DEFAULT, AIAgent
from chatballs.ai.provider.base import ProviderError
from chatballs.ai.pseudonymization import Pseudonymizer
from chatballs.ai.turn import (
    plan_chat,
    plan_query_embedding,
    record_turn,
    run_query_embedding,
    run_turn_chat,
    turn_pseudonymizer,
)
from chatballs.conversations import ai_turn_result, tool_call_events
from chatballs.conversations.ai_delivery import deliver as _deliver
from chatballs.conversations.ai_history import conversation_history as _history
from chatballs.conversations.models import (
    AiTurnState,
    ControlMode,
    Conversation,
    Message,
    MessageKind,
)
from chatballs.conversations.transcription import (
    TranscriptionJob,
    mark_transcription_failed,
    prepare_transcription,
    run_transcription,
    store_transcription,
)
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic

logger = logging.getLogger(__name__)

AI_TURN_REQUESTED = "conversation.ai_turn_requested"
# Агрегат события — диалог: ходы одного диалога обрабатываются строго по
# очереди (chatballs.events.services.claim_next_outbox_event).
AGGREGATE_TYPE = "Conversation"


@dataclass(slots=True)
class Turn:
    """Всё о ходе, прочитанное из базы первым шагом."""

    message: Message
    conversation: Conversation
    agent: AIAgent
    user_id: str
    query: str
    history: list[dict]
    # Карта токенов хода: одна на вектор вопроса и на запрос к модели, живёт
    # только в памяти (SPEC-0022 R-6).
    pseudonymizer: Pseudonymizer
    is_new_conversation: bool = False
    transcription_job: TranscriptionJob | None = None
    embedding_job: object | None = None
    # Ход прерван на подготовке, и клиенту есть что сказать: текст уходит ему
    # уже вне транзакции, как и обычный ответ.
    stopped: bool = False
    outgoing: str = ""


def request_ai_turn(
    *,
    message: Message,
    user_id: str,
    context: TenantContext,
    is_new_conversation: bool = False,
) -> None:
    """Шаг в транзакции приёма: пометить сообщение и поставить ход в очередь."""

    message.ai_turn_state = AiTurnState.PENDING
    message.save(update_fields=["ai_turn_state"])
    enqueue_event(
        DomainEvent(
            aggregate_type=AGGREGATE_TYPE,
            aggregate_id=str(message.conversation_id),
            event_type=AI_TURN_REQUESTED,
            payload={
                "messageId": message.id,
                "userId": user_id,
                # Про новый диалог операторов уже позвали при приёме: второй
                # оклик из-за нерасшифрованного голосового был бы лишним.
                "isNewConversation": is_new_conversation,
            },
            tenant_context=context,
        )
    )


def conversation_is_thinking(conversation_id: int) -> bool:
    """Есть ли по диалогу ход, который прямо сейчас считается.

    По этому же признаку виджет показывает клиенту, что ответ пишется.
    """
    return Message.objects.filter(
        conversation_id=conversation_id,
        ai_turn_state__in=(AiTurnState.PENDING, AiTurnState.RUNNING),
    ).exists()


def _time_left(message: Message) -> float:
    """Сколько секунд осталось до срока хода; он считается от прихода сообщения."""

    deadline = timedelta(seconds=settings.CHATBALLS_AI_TURN_DEADLINE_SECONDS)
    return (message.created_at + deadline - timezone.now()).total_seconds()


def _expired(message: Message) -> bool:
    return _time_left(message) < 0


def _plan_transcription(message: Message, channel) -> TranscriptionJob | None:
    """Голосовое без стенограммы: чем её снять. None — снимать нечем."""

    if message.kind != MessageKind.VOICE or message.transcript:
        return None
    try:
        return prepare_transcription(channel, message)
    except ProviderError as error:
        logger.info("Voice transcription unavailable for message %s: %s", message.id, error)
        return None


def _begin(*, message_id: int, user_id: str, is_new: bool, context: TenantContext) -> Turn | None:
    """Шаг в транзакции: взять ход в работу — или отказаться от него.

    Отказ здесь нормален и молчалив: событие могло приехать вторым заходом
    после сбоя, диалог мог уйти оператору, а ход мог пролежать в очереди
    дольше, чем ответ имеет смысл.
    """
    message = (
        Message.objects.select_related(
            "conversation__channel__ai_agent",
            "conversation__channel__organization",
            "conversation__contact",
            "conversation__connection",
        )
        .filter(id=message_id)
        .first()
    )
    if message is None:
        return None
    if message.ai_turn_state not in (AiTurnState.PENDING, AiTurnState.RUNNING):
        return None
    conversation = message.conversation
    channel = conversation.channel
    agent = getattr(channel, "ai_agent", None)
    if conversation.control_mode != ControlMode.AI or agent is None or not agent.is_active:
        # Диалог успел уйти человеку либо агента отключили: отвечать не нужно.
        message.ai_turn_state = AiTurnState.DONE
        message.save(update_fields=["ai_turn_state"])
        return None
    turn = Turn(
        message=message,
        conversation=conversation,
        agent=agent,
        user_id=user_id,
        query=message.text or message.transcript,
        history=_history(conversation, agent.history_limit or HISTORY_LIMIT_DEFAULT),
        pseudonymizer=turn_pseudonymizer(conversation),
        is_new_conversation=is_new,
    )
    message.ai_turn_state = AiTurnState.RUNNING
    message.save(update_fields=["ai_turn_state"])
    if _expired(message):
        turn.stopped = True
        turn.outgoing = ai_turn_result.store_failure(
            turn=turn, context=context, error="turn deadline passed"
        )
        return turn
    turn.transcription_job = _plan_transcription(message, channel)
    if turn.transcription_job is not None:
        # Вопрос станет известен после расшифровки — вместе с ним и вектор.
        return turn
    if not turn.query.strip():
        # Голосовое, которое нечем расшифровать, и прочее «отвечать не на что».
        ai_turn_result.store_voice_without_transcript(turn=turn, context=context)
        return None
    turn.embedding_job = plan_query_embedding(
        agent=agent, query=turn.query, pseudonymizer=turn.pseudonymizer
    )
    return turn


def _run_transcription(turn: Turn) -> str:
    """Шаг без транзакции: голос в текст."""

    try:
        return run_transcription(turn.transcription_job)
    except ProviderError as error:
        logger.info(
            "Voice transcription unavailable for message %s: %s", turn.message.id, error
        )
        return ""


def _apply_transcript(*, turn: Turn, transcript: str, context: TenantContext) -> bool:
    """Шаг в транзакции: сохранить стенограмму. False — хода не будет."""

    if not transcript.strip():
        mark_transcription_failed(turn.message)
        ai_turn_result.store_voice_without_transcript(turn=turn, context=context)
        return False
    store_transcription(turn.message, transcript)
    turn.query = transcript
    turn.embedding_job = plan_query_embedding(
        agent=turn.agent, query=transcript, pseudonymizer=turn.pseudonymizer
    )
    return True


def run_requested_turn(payload: dict, context: TenantContext) -> None:
    """Ход целиком: короткие транзакции и походы наружу между ними."""

    message_id = int(payload.get("messageId") or 0)
    user_id = str(payload.get("userId") or "")
    is_new = bool(payload.get("isNewConversation"))
    with tenant_atomic(context):
        turn = _begin(message_id=message_id, user_id=user_id, is_new=is_new, context=context)
    if turn is None:
        return
    if turn.stopped:
        _deliver(turn, turn.outgoing)
        return

    if turn.transcription_job is not None:
        transcript = _run_transcription(turn)
        with tenant_atomic(context):
            if not _apply_transcript(turn=turn, transcript=transcript, context=context):
                return

    embedding = run_query_embedding(turn.embedding_job)
    failure = None
    with tenant_atomic(context):
        try:
            plan = plan_chat(
                agent=turn.agent,
                message=turn.query,
                history=turn.history,
                embedding=embedding,
                conversation=turn.conversation,
                pseudonymizer=turn.pseudonymizer,
            )
            start_diagnostic(turn.message, plan)
        except ProviderError as error:
            # Провайдер не настроен вовсе — тот же отказ хода, что и молчание
            # модели: клиент получает понятный текст, диалог уходит человеку.
            failure = ai_turn_result.store_failure(turn=turn, context=context, error=error)
            record_planning_failure(turn.message, turn.agent, turn.conversation,
                                    turn.pseudonymizer, error)
    if failure is not None:
        _deliver(turn, failure)
        return

    # Вызовы инструментов агента укладываются в тот же срок хода.
    answer = run_turn_chat(plan, time_left=_time_left(turn.message))
    with tenant_atomic(context):
        # В диалог и клиенту идёт ответ с настоящими значениями вместо токенов.
        finish_diagnostic(turn.message, plan, answer)
        reply = record_turn(agent=turn.agent, plan=plan, answer=answer)
        tool_call_events.record_tool_calls(turn.message, answer.tool_calls)
        if answer.error is not None:
            outgoing = ai_turn_result.store_failure(
                turn=turn, context=context, error=answer.error
            )
        else:
            outgoing = ai_turn_result.store_answer(turn=turn, context=context, text=reply)
    _deliver(turn, outgoing)
