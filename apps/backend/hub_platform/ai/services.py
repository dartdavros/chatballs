from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

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


def _knowledge_for_ids(*, context: TenantContext, knowledge_ids: list[int]) -> list[Knowledge]:
    items = list(Knowledge.objects.filter(organization=context.organization, id__in=knowledge_ids))
    if len(items) != len(set(knowledge_ids)):
        raise ValidationError({"knowledgeIds": "Unknown knowledge item"})
    return items


@transaction.atomic
def create_agent(*, context: TenantContext, data: AgentCreateInput) -> AIAgent:
    organization = context.organization
    if not data.channel_code:
        raise ValidationError({"channel": "Channel is required"})
    try:
        channel = Channel.objects.get(organization=organization, code=data.channel_code)
    except Channel.DoesNotExist as error:
        raise ValidationError({"channel": "Channel not found"}) from error
    if AIAgent.objects.filter(channel=channel).exists():
        raise ValidationError({"channel": "Channel already has an AI agent"})

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
    agent.knowledge_items.set(_knowledge_for_ids(context=context, knowledge_ids=data.knowledge_ids))
    return agent


@transaction.atomic
def update_agent(*, context: TenantContext, agent: AIAgent, data: AgentInput) -> AIAgent:
    if agent.channel.organization_id != context.organization_id:
        raise ValidationError({"agent": "Agent belongs to another organization"})
    agent.name = data.name
    mode, agent.model = configure_agent_provider(
        context=context,
        channel=agent.channel,
        mode=data.credential_mode,
        integration_id=data.provider_integration_id,
    )
    agent.credential_mode = mode
    agent.model_params = data.model_params
    agent.allowed_tools = data.allowed_tools
    agent.limits = _normalize_limits(data.limits)
    agent.persona = data.persona
    agent.tone = data.tone
    agent.instructions = data.instructions
    agent.save(
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
    if data.knowledge_ids is not None:
        agent.knowledge_items.set(
            _knowledge_for_ids(context=context, knowledge_ids=data.knowledge_ids)
        )
    return agent


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
