from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from chatballs.ai.agent_knowledge import knowledge_available_to_channel
from chatballs.ai.models import (
    AIAgent,
    AIAgentStatus,
    Knowledge,
)
from chatballs.ai.provider_selection import (
    configure_agent_provider,
    configure_agent_transcription,
)
from chatballs.channels.models import Channel
from chatballs.i18n import t
from chatballs.tenancy.context import TenantContext


@dataclass(frozen=True)
class AgentInput:
    name: str
    provider_integration_id: int | None
    # Чем расшифровывать голосовые; None — тем же провайдером, что и отвечает.
    transcription_integration_id: int | None
    # Модели агента; пустая строка — «как в интеграции».
    model: str
    transcription_model: str
    model_params: dict
    allowed_tools: list
    persona: str
    tone: str
    instructions: str
    answer_language: str
    history_limit: int
    knowledge_ids: list[int] | None  # None -> выбор знаний не меняется
    assistance_enabled: bool | None = None  # None -> legacy-клиент не меняет помощь
    transcription_language: str = ""
    synthesis_integration_id: int | None = None
    synthesis_model: str = ""
    synthesis_voice: str = ""


@dataclass(frozen=True)
class AgentCreateInput:
    channel_code: str
    provider_integration_id: int | None
    persona: str
    tone: str
    instructions: str
    knowledge_ids: list[int]


def knowledge_for_agent_ids(
    *, context: TenantContext, channel: Channel, knowledge_ids: list[int]
) -> list[Knowledge]:
    requested_ids = set(knowledge_ids)
    available_ids = knowledge_available_to_channel(
        Knowledge.objects.filter(
            organization_id=context.organization_id,
            id__in=requested_ids,
        ),
        channel=channel,
    ).values("id")
    items = list(
        Knowledge.objects.select_for_update()
        .filter(
            organization_id=context.organization_id,
            id__in=available_ids,
        )
        .order_by("id")
    )
    if len(items) != len(requested_ids):
        raise ValidationError({"knowledgeIds": t("ai.knowledge_unknown_or_unavailable")})
    return items


@transaction.atomic
def create_agent(*, context: TenantContext, data: AgentCreateInput) -> AIAgent:
    organization = context.organization
    if not data.channel_code:
        raise ValidationError({"channel": t("ai.channel_required")})
    try:
        channel = Channel.objects.select_for_update().get(
            organization=organization,
            code=data.channel_code,
        )
    except Channel.DoesNotExist as error:
        raise ValidationError({"channel": t("channels.not_found")}) from error
    if AIAgent.objects.filter(channel=channel).exists():
        raise ValidationError({"channel": t("channels.agent_exists")})

    knowledge_items = knowledge_for_agent_ids(
        context=context,
        channel=channel,
        knowledge_ids=data.knowledge_ids,
    )
    selection = configure_agent_provider(
        context=context,
        integration_id=data.provider_integration_id,
    )
    agent = AIAgent.objects.create(
        channel=channel,
        name=f"{channel.name} Agent",
        status=AIAgentStatus.DRAFT,
        # Модель новой карточки не фиксируется: агент следует за интеграцией,
        # пока человек не выберет свою.
        model="",
        provider_integration=selection.integration,
        persona=data.persona,
        tone=data.tone,
        instructions=data.instructions,
    )
    agent.knowledge_items.set(knowledge_items)
    return agent


@transaction.atomic
def update_agent(*, context: TenantContext, agent: AIAgent, data: AgentInput) -> AIAgent:
    if agent.channel.organization_id != context.organization_id:
        raise ValidationError({"agent": t("ai.agent_other_organization")})
    channel = Channel.objects.select_for_update().get(
        id=agent.channel_id,
        organization_id=context.organization_id,
    )
    knowledge_items = None
    if data.knowledge_ids is not None:
        knowledge_items = knowledge_for_agent_ids(
            context=context,
            channel=channel,
            knowledge_ids=data.knowledge_ids,
        )
    locked = AIAgent.objects.select_for_update().get(
        id=agent.id,
        channel=channel,
    )
    locked.name = data.name
    selection = configure_agent_provider(
        context=context,
        integration_id=data.provider_integration_id,
    )
    # Модель выбирают на карточке агента: на одном ключе провайдера живут разные
    # агенты, и модель им нужна разная. Пустое поле означает «как в интеграции»
    # и разрешается в момент вызова (ai.provider.routing).
    locked.model = data.model.strip()[:128]
    locked.transcription_model = data.transcription_model.strip()[:128]
    # Провайдер живёт на агенте: канал больше не изменяется при сохранении агента.
    locked.provider_integration = selection.integration
    locked.transcription_integration = configure_agent_transcription(
        context=context,
        integration_id=data.transcription_integration_id,
    )
    from chatballs.speech.agent_configuration import validate_agent_speech

    validate_agent_speech(locked, language=data.transcription_language)
    locked.transcription_language = data.transcription_language
    from chatballs.speech.agent_configuration import configure_agent_synthesis

    configure_agent_synthesis(context, locked, integration_id=data.synthesis_integration_id,
                              model=data.synthesis_model, voice=data.synthesis_voice)
    locked.model_params = data.model_params
    locked.allowed_tools = data.allowed_tools
    locked.persona = data.persona
    locked.tone = data.tone
    locked.instructions = data.instructions
    locked.answer_language = data.answer_language
    locked.history_limit = data.history_limit
    if data.assistance_enabled is not None:
        if not isinstance(data.assistance_enabled, bool):
            raise ValidationError({"assistanceEnabled": t("api.boolean_required")})
        locked.assistance_enabled = data.assistance_enabled
    locked.save(
        update_fields=[
            "name",
            "model",
            "transcription_model",
            "transcription_language",
            "synthesis_integration", "synthesis_model", "synthesis_voice",
            "provider_integration",
            "transcription_integration",
            "model_params",
            "allowed_tools",
            "persona",
            "tone",
            "instructions",
            "answer_language",
            "history_limit",
            "assistance_enabled",
            "updated_at",
        ]
    )
    if knowledge_items is not None:
        locked.knowledge_items.set(knowledge_items)
    return locked


@transaction.atomic
def set_agent_active(*, context: TenantContext, agent: AIAgent, is_active: bool) -> AIAgent:
    """Смена статуса AI без тарифных слотов (ADR-CHATBALLS-0042 §2): количество
    активных агентов не ограничено; активация требует настроенного провайдера."""
    if agent.channel.organization_id != context.organization_id:
        raise ValidationError({"agent": t("ai.agent_other_organization")})
    locked = AIAgent.objects.select_for_update().get(
        pk=agent.id, organization_id=context.organization_id
    )
    target_status = AIAgentStatus.ACTIVE if is_active else AIAgentStatus.DISABLED
    if locked.status == target_status:
        return locked
    if locked.status == AIAgentStatus.ARCHIVED:
        raise ValidationError({"agent": t("ai.archived_agent_state")})
    if is_active and locked.provider_integration_id is None:
        raise ValidationError(
            {"providerIntegrationId": t("ai.pick_provider_first")}
        )
    locked.status = target_status
    locked.lifecycle_version += 1
    locked.save(update_fields=["status", "lifecycle_version", "updated_at"])
    from chatballs.identity.audit import record_audit_event

    record_audit_event(
        action="ai.agent_status_changed",
        actor=context.actor_user,
        organization=context.organization,
        object_type="AIAgent",
        object_id=str(locked.id),
        payload={"current": target_status},
    )
    return locked


from chatballs.ai.knowledge_services import (  # noqa: E402, F401
    KnowledgeInput,
    add_attachment,
    create_knowledge,
    delete_attachment,
    delete_knowledge,
    update_knowledge,
)
