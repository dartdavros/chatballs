from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from chatballs.ai.agent_knowledge import knowledge_available_to_channel
from chatballs.ai.models import (
    AIAgent,
    AIAgentStatus,
    Knowledge,
)
from chatballs.ai.provider_selection import configure_agent_provider
from chatballs.channels.models import Channel
from chatballs.tenancy.context import TenantContext


@dataclass(frozen=True)
class AgentInput:
    name: str
    provider_integration_id: int | None
    model_params: dict
    allowed_tools: list
    limits: dict
    persona: str
    tone: str
    instructions: str
    knowledge_ids: list[int] | None  # None -> выбор знаний не меняется


@dataclass(frozen=True)
class AgentCreateInput:
    channel_code: str
    provider_integration_id: int | None
    persona: str
    tone: str
    instructions: str
    knowledge_ids: list[int]


# Единственный поддерживаемый лимит агента — дневной бюджет в целых центах USD
# (dailyCostUsd). Прочие исторические ключи (dailyCostMicros, dailyBudgetRub,
# dailyDialogs, maxMessagesPerDialog) бэкендом не используются и отбрасываются.
def _normalize_limits(raw: dict | None) -> dict:
    if not isinstance(raw, dict):
        return {}
    value = raw.get("dailyCostUsd")
    try:
        cents = int(value)
    except (TypeError, ValueError):
        return {}
    return {"dailyCostUsd": cents} if cents > 0 else {}


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
        raise ValidationError({"knowledgeIds": "Unknown or unavailable knowledge item"})
    return items


@transaction.atomic
def create_agent(*, context: TenantContext, data: AgentCreateInput) -> AIAgent:
    organization = context.organization
    if not data.channel_code:
        raise ValidationError({"channel": "Channel is required"})
    try:
        channel = Channel.objects.select_for_update().get(
            organization=organization,
            code=data.channel_code,
        )
    except Channel.DoesNotExist as error:
        raise ValidationError({"channel": "Channel not found"}) from error
    if AIAgent.objects.filter(channel=channel).exists():
        raise ValidationError({"channel": "Channel already has an AI agent"})

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
        model=selection.model,
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
        raise ValidationError({"agent": "Agent belongs to another organization"})
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
    # Модель принадлежит интеграции; без провайдера прежняя модель сохраняется,
    # чтобы PATCH инструкций не стирал её у черновика.
    locked.model = selection.model if selection.integration else locked.model
    # Провайдер живёт на агенте: канал больше не изменяется при сохранении агента.
    locked.provider_integration = selection.integration
    locked.model_params = data.model_params
    locked.allowed_tools = data.allowed_tools
    locked.limits = _normalize_limits(data.limits)
    locked.persona = data.persona
    locked.tone = data.tone
    locked.instructions = data.instructions
    locked.save(
        update_fields=[
            "name",
            "model",
            "provider_integration",
            "model_params",
            "allowed_tools",
            "limits",
            "persona",
            "tone",
            "instructions",
            "updated_at",
        ]
    )
    if knowledge_items is not None:
        locked.knowledge_items.set(knowledge_items)
    return locked


@transaction.atomic
def set_agent_active(*, context: TenantContext, agent: AIAgent, is_active: bool) -> AIAgent:
    """Смена статуса AI без тарифных слотов (ADR-HUB-0042 §2): количество
    активных агентов не ограничено; активация требует настроенного провайдера."""
    if agent.channel.organization_id != context.organization_id:
        raise ValidationError({"agent": "Agent belongs to another organization"})
    locked = AIAgent.objects.select_for_update().get(
        pk=agent.id, organization_id=context.organization_id
    )
    target_status = AIAgentStatus.ACTIVE if is_active else AIAgentStatus.DISABLED
    if locked.status == target_status:
        return locked
    if locked.status == AIAgentStatus.ARCHIVED:
        raise ValidationError({"agent": "Archived AI agent cannot change state"})
    if is_active and locked.provider_integration_id is None:
        raise ValidationError(
            {"providerIntegrationId": "Для запуска AI выберите провайдера организации"}
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
