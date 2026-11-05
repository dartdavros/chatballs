"""Агент как единая сущность (ADR-CHATBALLS-0041 §4, SPEC-CHATBALLS-0031 §4.3).

Для администратора существует только «Агент»: имя, группа, инструкции, знания,
подключения, активность. Физически карточка агрегирует Channel (несущая ось
диалогов/подключений) и AIAgent (конфигурация AI) 1:1; id карточки — id канала.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, QuerySet, Value, When
from django.utils.text import slugify

from chatballs.ai.agent_card_payload import (
    agent_card_payload as agent_card_payload,
)
from chatballs.ai.agent_card_payload import (
    knowledge_total_for_organization as knowledge_total_for_organization,
)
from chatballs.ai.models import (
    HISTORY_LIMIT_MAX,
    AIAgent,
    AIAgentStatus,
    AnswerLanguage,
    ReplyAssistanceAttempt,
)
from chatballs.channels.models import Channel
from chatballs.channels.services import (
    CODE_MAX_LENGTH,
    UNSET,
    ChannelUpdate,
    update_channel,
)
from chatballs.conversations.models import LifecycleState
from chatballs.i18n import normalize_language, t
from chatballs.tenancy.context import TenantContext


def agent_cards_for_context(context: TenantContext) -> QuerySet[Channel]:
    return (
        Channel.objects.filter(organization_id=context.organization_id, ai_agent__isnull=False)
        .select_related("group", "ai_agent", "ai_agent__provider_integration")
        .prefetch_related(
            "connections__web_chat_widget",
            "ai_agent__knowledge_items",
            "ai_agent__portal_articles__portal",
            "ai_agent__portal_articles__published_revision",
        )
        .annotate(
            open_conversations_count=Count(
                "conversations",
                filter=Q(conversations__lifecycle=LifecycleState.OPEN),
                distinct=True,
            ),
            # Кадр G1: сверху отвечающие агенты, ниже «Без AI», выключенные — в конце.
            status_rank=Case(
                When(is_active=False, then=Value(2)),
                When(ai_agent__status=AIAgentStatus.ACTIVE, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        )
        .order_by("status_rank", "name")
    )


def agent_card_for_context(*, context: TenantContext, agent_id: int) -> Channel:
    return agent_cards_for_context(context).get(id=agent_id)


def _unique_agent_code(organization_id: int, name: str) -> str:
    base = slugify(name)[: CODE_MAX_LENGTH - 8].strip("-") or "agent"
    taken = set(
        Channel.objects.filter(
            organization_id=organization_id, code__startswith=base
        ).values_list("code", flat=True)
    )
    if base not in taken:
        return base
    for suffix in range(2, 1000):
        candidate = f"{base}-{suffix}"
        if candidate not in taken:
            return candidate
    raise ValidationError({"name": t("ai.agent_code_collision")})


def ensure_channel_agent(channel: Channel) -> AIAgent:
    """AIAgent обязателен для каждого канала: DRAFT = AI не отвечает."""
    agent = getattr(channel, "ai_agent", None)
    if agent is not None:
        return agent
    agent = AIAgent.objects.create(
        channel=channel,
        name=channel.name,
        status=AIAgentStatus.DRAFT,
    )
    # Обновляем кеш select_related, чтобы payload не перечитывал канал.
    channel.ai_agent = agent
    return agent


@transaction.atomic
def create_agent_card(
    *, context: TenantContext, name: object, group_id: int | None
) -> Channel:
    """Мастер одного шага (SPEC-CHATBALLS-0031 §4.3): имя и необязательная группа.

    Канал создаётся без продукта с безопасной операторской политикой (дефолты
    модели удовлетворяют P1-P5); код генерируется из имени и неизменен.
    """
    from chatballs.channels import authorization
    from chatballs.channels.services import _clean_name, _group_for_channel

    authorization.require_organization_manage(context, operation="channels.operation_agent_create")
    clean_name = _clean_name(name)
    group = _group_for_channel(context=context, group_id=group_id)
    channel = Channel.objects.create(
        organization_id=context.organization_id,
        code=_unique_agent_code(context.organization_id, clean_name),
        name=clean_name,
        group=group,
    )
    ensure_channel_agent(channel)
    return channel


@transaction.atomic
def update_agent_card(
    *, context: TenantContext, channel: Channel, body: dict[str, object]
) -> Channel:
    """PATCH одной карточки: канальные и AI-поля в одной транзакции."""
    agent = ensure_channel_agent(channel)

    update = ChannelUpdate(
        name=body["name"] if "name" in body else UNSET,
        group_id=body["groupId"] if "groupId" in body else UNSET,
        is_active=body["isActive"] if "isActive" in body else UNSET,
    )
    channel = update_channel(context=context, channel=channel, update=update)

    ai_fields = {
        "providerIntegrationId",
        "transcriptionIntegrationId",
        "model",
        "transcriptionModel",
        "transcriptionLanguage",
        "synthesisIntegrationId", "synthesisModel", "synthesisVoice",
        "modelParams",
        "persona",
        "tone",
        "instructions",
        "answerLanguage",
        "historyLimit",
        "assistanceEnabled",
        "knowledgeIds",
    }
    if ai_fields & set(body):
        from chatballs.ai.services import AgentInput, update_agent

        if "assistanceEnabled" in body and not isinstance(body["assistanceEnabled"], bool):
            raise ValidationError({"assistanceEnabled": t("api.boolean_required")})
        knowledge_ids = body.get("knowledgeIds")
        if knowledge_ids is not None and (
            not isinstance(knowledge_ids, list)
            or not all(isinstance(item, int) for item in knowledge_ids)
        ):
            raise ValidationError({"knowledgeIds": t("api.list_of_ids_required")})
        model_params = body.get("modelParams", agent.model_params)
        if not isinstance(model_params, dict):
            raise ValidationError({"modelParams": t("api.object_required")})
        provider_integration_id = body.get(
            "providerIntegrationId", agent.provider_integration_id
        )
        if provider_integration_id is not None and not isinstance(
            provider_integration_id, int
        ):
            raise ValidationError({"providerIntegrationId": t("api.integer_id_required")})
        transcription_integration_id = body.get(
            "transcriptionIntegrationId", agent.transcription_integration_id
        )
        if transcription_integration_id is not None and not isinstance(
            transcription_integration_id, int
        ):
            raise ValidationError(
                {"transcriptionIntegrationId": t("api.integer_id_required")}
            )
        update_agent(
            context=context,
            agent=agent,
            data=AgentInput(
                # Имя агента следует за именем карточки: сущность одна.
                name=channel.name,
                provider_integration_id=provider_integration_id,
                transcription_integration_id=transcription_integration_id,
                model=str(body.get("model", agent.model)),
                transcription_model=str(
                    body.get("transcriptionModel", agent.transcription_model)
                ),
                model_params=model_params,
                transcription_language=body.get("transcriptionLanguage", agent.transcription_language),
                synthesis_integration_id=body.get("synthesisIntegrationId", agent.synthesis_integration_id),
                synthesis_model=body.get("synthesisModel", agent.synthesis_model),
                synthesis_voice=body.get("synthesisVoice", agent.synthesis_voice),
                allowed_tools=agent.allowed_tools,
                persona=str(body.get("persona", agent.persona)),
                tone=str(body.get("tone", agent.tone)),
                instructions=str(body.get("instructions", agent.instructions)),
                answer_language=_clean_answer_language(
                    body.get("answerLanguage", agent.answer_language)
                ),
                history_limit=_clean_history_limit(
                    body.get("historyLimit", agent.history_limit)
                ),
                knowledge_ids=knowledge_ids,
                assistance_enabled=body.get("assistanceEnabled", agent.assistance_enabled),
            ),
        )
    elif update.name is not UNSET:
        agent.name = channel.name
        agent.save(update_fields=["name", "updated_at"])
    if "tools" in body:
        from chatballs.ai.agent_tools import set_agent_tools

        set_agent_tools(agent=agent, raw=body["tools"])
    return agent_card_for_context(context=context, agent_id=channel.id)


def _clean_answer_language(value: object) -> str:
    """Режим ответа агента: MIRROR, ORGANIZATION или код поддерживаемого языка."""

    raw = str(value or "").strip()
    if raw in AnswerLanguage.values:
        return raw
    code = normalize_language(raw)
    if code:
        return code
    raise ValidationError({"answerLanguage": t("ai.unknown_answer_language")})


def _clean_history_limit(value: object) -> int:
    """Окно истории агента: целое число сообщений от 1 до HISTORY_LIMIT_MAX."""

    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= HISTORY_LIMIT_MAX:
        raise ValidationError(
            {"historyLimit": t("ai.history_limit_out_of_range", max=HISTORY_LIMIT_MAX)}
        )
    return value


def agent_deletion_blockers(channel: Channel) -> list[dict[str, object]]:
    """Агент удаляется вместе с каналом; блокируют только внешние связи."""
    counts = (
        ("conversations", channel.conversations.count()),
        ("connections", channel.connections.count()),
        ("llmInvocations", channel.ai_invocations.count()),
        ("replyAssistanceAttempts", ReplyAssistanceAttempt.objects.filter(agent__channel=channel).count()),
    )
    return [{"type": name, "count": count} for name, count in counts if count]


@transaction.atomic
def delete_agent_card(*, context: TenantContext, channel: Channel) -> None:
    from chatballs.channels import authorization
    from chatballs.channels.services import ChannelHasReferences

    authorization.require_organization_manage(context, operation="channels.operation_agent_delete")
    blockers = agent_deletion_blockers(channel)
    if blockers:
        raise ChannelHasReferences(blockers)
    AIAgent.objects.filter(channel=channel).delete()
    channel.delete()


def set_agent_card_active(
    *, context: TenantContext, channel: Channel, is_active: bool
) -> Channel:
    """Активность AI: включает/выключает автоответы, канал остаётся живым."""
    from chatballs.ai.services import set_agent_active

    agent = ensure_channel_agent(channel)
    set_agent_active(context=context, agent=agent, is_active=is_active)
    return agent_card_for_context(context=context, agent_id=channel.id)
