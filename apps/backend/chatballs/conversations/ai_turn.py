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
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from chatballs.ai.diagnostic_capture import (
    record_planning_failure,
    start_diagnostic,
)
from chatballs.ai.models import HISTORY_LIMIT_DEFAULT
from chatballs.ai.provider.base import ProviderError
from chatballs.ai.turn import (
    plan_chat,
    plan_query_embedding,
    run_query_embedding,
    run_turn_chat,
    turn_pseudonymizer,
)
from chatballs.conversations import ai_turn_result
from chatballs.conversations.ai_delivery import deliver as _deliver
from chatballs.conversations.ai_history import conversation_history as _history
from chatballs.conversations.ai_reply_delivery import deliver_saved
from chatballs.conversations.ai_turn_completion import (
    finish_requested_turn,
    store_failure_if_current,
)
from chatballs.conversations.ai_turn_state import (
    AI_TURN_REQUESTED as AI_TURN_REQUESTED,
)
from chatballs.conversations.ai_turn_state import (
    Turn,
)
from chatballs.conversations.ai_turn_state import (
    conversation_is_thinking as conversation_is_thinking,
)
from chatballs.conversations.ai_turn_state import (
    request_ai_turn as request_ai_turn,
)
from chatballs.conversations.models import (
    AiTurnState,
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
from chatballs.identity.operation_modes import autonomous_allowed, lock_organization
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic

logger = logging.getLogger(__name__)


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
    organization = lock_organization(context.organization_id)
    message = (
        Message.objects.select_related(
            "conversation__channel__ai_agent",
            "conversation__channel__organization",
            "conversation__contact",
            "conversation__connection",
        )
        .filter(id=message_id, organization_id=context.organization_id)
        .first()
    )
    if message is None:
        return None
    conversation = Conversation.objects.select_for_update(of=("self",)).select_related(
        "channel__ai_agent", "channel__organization", "contact", "connection",
    ).get(pk=message.conversation_id, organization_id=context.organization_id)
    message = Message.objects.select_for_update().get(pk=message.pk, organization_id=context.organization_id)
    message.conversation = conversation
    if message.ai_turn_state not in (AiTurnState.PENDING, AiTurnState.RUNNING):
        return None
    conversation = message.conversation
    channel = conversation.channel
    agent = getattr(channel, "ai_agent", None)
    if (not autonomous_allowed(channel, organization=organization,
                               connection=conversation.connection, conversation=conversation)
            or message.ai_delivery.get("modeVersion", 1) != organization.operation_mode_version
            or message.ai_delivery.get("controlVersion", 0) != conversation.ai_control_version
            or message.ai_delivery.get("agentId", agent.pk if agent else None) != (agent.pk if agent else None)):
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
        mode_version=organization.operation_mode_version,
        control_version=conversation.ai_control_version,
    )
    message.ai_turn_state = AiTurnState.RUNNING
    message.save(update_fields=["ai_turn_state"])
    if _expired(message):
        turn.stopped = True
        turn.outgoing = store_failure_if_current(
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

    from chatballs.conversations.ai_turn_completion import refresh_turn_control

    if not refresh_turn_control(turn, context):
        return False
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
        deliver_saved(message_id, context)
        return
    if turn.stopped:
        _deliver(turn, turn.outgoing, context)
        return

    from chatballs.conversations.autonomous_execution import guarded_call

    if turn.transcription_job is not None:
        transcript = guarded_call(turn, context, _run_transcription, turn)
        if transcript is None:
            return
        with tenant_atomic(context):
            if not _apply_transcript(turn=turn, transcript=transcript, context=context):
                return

    embedding = guarded_call(turn, context, run_query_embedding, turn.embedding_job)
    failure = None
    with tenant_atomic(context):
        from chatballs.conversations.ai_turn_completion import refresh_turn_control

        if not refresh_turn_control(turn, context):
            return
        try:
            plan = plan_chat(
                agent=turn.agent,
                message=turn.query,
                history=turn.history,
                embedding=embedding,
                conversation=turn.conversation,
                action_turn_id=turn.message.pk,
                pseudonymizer=turn.pseudonymizer,
            )
            start_diagnostic(turn.message, plan)
        except ProviderError as error:
            # Провайдер не настроен вовсе — тот же отказ хода, что и молчание
            # модели: клиент получает понятный текст, диалог уходит человеку.
            failure = store_failure_if_current(turn=turn, context=context, error=error)
            record_planning_failure(turn.message, turn.agent, turn.conversation,
                                    turn.pseudonymizer, error)
    if failure is not None:
        _deliver(turn, failure, context)
        return

    # Вызовы инструментов агента укладываются в тот же срок хода.
    answer = guarded_call(turn, context, run_turn_chat, plan, time_left=_time_left(turn.message))
    if answer is None:
        return
    with tenant_atomic(context):
        outgoing = finish_requested_turn(turn, context, plan, answer)
    _deliver(turn, outgoing, context)
