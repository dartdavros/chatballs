"""Persisted scheduling and display state for autonomous conversation turns."""

from dataclasses import dataclass

from django.db.models import BigIntegerField, F, Value
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce

from chatballs.ai.models import AIAgent
from chatballs.ai.pseudonymization import Pseudonymizer
from chatballs.conversations.models import AiTurnState, ControlMode, Conversation, Message
from chatballs.conversations.transcription import TranscriptionJob
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.identity.operation_modes import autonomous_allowed, lock_organization
from chatballs.tenancy.context import TenantContext

AI_TURN_REQUESTED = "conversation.ai_turn_requested"
AGGREGATE_TYPE = "Conversation"

@dataclass(slots=True)
class Turn:
    """Всё о ходе, прочитанное из базы первым шагом."""

    message: Message | None
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
    mode_version: int = 0
    control_version: int = 0
    site_event_launch_id: int | None = None


def request_ai_turn(
    *,
    message: Message,
    user_id: str,
    context: TenantContext,
    is_new_conversation: bool = False,
) -> None:
    """Шаг в транзакции приёма: пометить сообщение и поставить ход в очередь."""

    organization = lock_organization(context.organization_id)
    conversation = Conversation.objects.select_for_update(of=("self",)).select_related("channel__ai_agent", "connection").get(
        pk=message.conversation_id, organization_id=context.organization_id,
    )
    if not autonomous_allowed(conversation.channel, organization=organization,
                              connection=conversation.connection, conversation=conversation):
        return
    message.ai_turn_state = AiTurnState.PENDING
    message.ai_delivery = {"modeVersion": organization.operation_mode_version,
                           "controlVersion": conversation.ai_control_version,
                           "agentId": conversation.channel.ai_agent.pk}
    message.save(update_fields=["ai_turn_state", "ai_delivery"])
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
    return Message.objects.annotate(
        turn_mode_version=Coalesce(Cast(KeyTextTransform("modeVersion", "ai_delivery"), BigIntegerField()), Value(1), output_field=BigIntegerField()),
    ).filter(
        turn_mode_version=F("organization__operation_mode_version"),
        conversation_id=conversation_id,
        ai_turn_state__in=(AiTurnState.PENDING, AiTurnState.RUNNING),
        conversation__control_mode=ControlMode.AI,
        conversation__organization__operation_mode="AI_AGENTS",
    ).exists()
