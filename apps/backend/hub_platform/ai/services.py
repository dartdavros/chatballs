from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from hub_platform.ai.agent_knowledge import knowledge_available_to_channel
from hub_platform.ai.models import (
    AIAgent,
    AIAgentStatus,
    Knowledge,
)
from hub_platform.ai.provider_selection import configure_agent_provider
from hub_platform.channels.models import Channel
from hub_platform.tenancy.context import TenantContext


@dataclass(frozen=True)
class AgentInput:
    name: str
    credential_mode: str
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
    credential_mode: str
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
    mode, model = configure_agent_provider(
        context=context,
        channel=channel,
        mode=data.credential_mode,
        integration_id=data.provider_integration_id,
    )
    agent = AIAgent.objects.create(
        channel=channel,
        name=f"{channel.name} Agent",
        status=AIAgentStatus.DRAFT,
        model=model,
        credential_mode=mode,
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
    mode, locked.model = configure_agent_provider(
        context=context,
        channel=channel,
        mode=data.credential_mode,
        integration_id=data.provider_integration_id,
    )
    locked.credential_mode = mode
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
            "credential_mode",
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


def set_agent_active(*, context: TenantContext, agent: AIAgent, is_active: bool) -> AIAgent:
    if agent.channel.organization_id != context.organization_id:
        raise ValidationError({"agent": "Agent belongs to another organization"})
    from hub_platform.subscriptions.agent_slots import set_agent_status

    return set_agent_status(
        context=context,
        agent_id=agent.id,
        target_status=AIAgentStatus.ACTIVE if is_active else AIAgentStatus.DISABLED,
    )


from hub_platform.ai.knowledge_services import (  # noqa: E402, F401
    KnowledgeInput,
    add_attachment,
    create_knowledge,
    delete_attachment,
    delete_knowledge,
    update_knowledge,
)
