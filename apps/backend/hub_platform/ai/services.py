from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from hub_platform.ai import releases as release_service
from hub_platform.ai.models import (
    AIAgent,
    DocumentScope,
    DocumentStatus,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    PromptCategory,
    PromptDocument,
    PromptDocumentVersion,
)
from hub_platform.channels.models import Channel


@dataclass(frozen=True)
class AgentInput:
    name: str
    model: str
    model_params: dict
    allowed_tools: list
    limits: dict


@dataclass(frozen=True)
class AgentCreateInput:
    channel_code: str
    model: str
    system_prompt: str
    knowledge_document_ids: list[int]


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


START_PROMPTS: tuple[tuple[str, str, str], ...] = (
    ("system", "Системный prompt", PromptCategory.SYSTEM),
    ("qualification", "Квалификация", PromptCategory.QUALIFICATION),
    ("sales-behavior", "Поведение в продаже", PromptCategory.SALES_BEHAVIOR),
    ("operator-handoff", "Передача оператору", PromptCategory.OPERATOR_HANDOFF),
)


def _next_prompt_version(document: PromptDocument) -> int:
    latest = document.versions.order_by("-version").first()
    return latest.version + 1 if latest else 1


def _create_prompt_versions(*, channel: Channel, author, system_prompt: str) -> list[PromptDocumentVersion]:
    scope = DocumentScope.PRODUCT if channel.product_id else DocumentScope.GLOBAL
    versions = []
    for code, title, category in START_PROMPTS:
        document, _ = PromptDocument.objects.get_or_create(
            organization=channel.organization,
            product=channel.product,
            code=code,
            defaults={"title": title, "category": category, "scope": scope},
        )
        content = system_prompt if category == PromptCategory.SYSTEM else ""
        versions.append(
            PromptDocumentVersion.objects.create(
                document=document,
                version=_next_prompt_version(document),
                content=content,
                status=DocumentStatus.DRAFT,
                created_by=author,
            )
        )
    return versions


def _selected_knowledge_versions(*, organization, document_ids: list[int]) -> list[KnowledgeDocumentVersion]:
    documents = KnowledgeDocument.objects.filter(organization=organization, id__in=document_ids, is_enabled=True).prefetch_related("versions")
    if documents.count() != len(set(document_ids)):
        raise ValidationError({"knowledgeDocumentIds": "Unknown knowledge document"})
    versions = []
    for document in documents:
        version = document.versions.order_by("-version").first()
        if version is None:
            raise ValidationError({"knowledgeDocumentIds": "Knowledge document has no versions"})
        versions.append(version)
    return versions


@transaction.atomic
def create_agent(*, organization, author, data: AgentCreateInput) -> tuple[AIAgent, object]:
    if not data.channel_code:
        raise ValidationError({"channel": "Channel is required"})
    if not data.model:
        raise ValidationError({"model": "Model is required"})
    try:
        channel = Channel.objects.get(organization=organization, code=data.channel_code)
    except Channel.DoesNotExist as error:
        raise ValidationError({"channel": "Channel not found"}) from error
    if AIAgent.objects.filter(channel=channel).exists():
        raise ValidationError({"channel": "Channel already has an AI agent"})

    agent = AIAgent.objects.create(
        channel=channel,
        name=f"{channel.name} Agent",
        is_active=False,
        model=data.model,
    )
    knowledge_versions = _selected_knowledge_versions(organization=organization, document_ids=data.knowledge_document_ids)
    prompt_versions = _create_prompt_versions(channel=channel, author=author, system_prompt=data.system_prompt)
    release = release_service.create_initial_draft_release(
        channel=channel,
        author=author,
        model=agent.model,
        model_params=agent.model_params,
        allowed_tools=agent.allowed_tools,
        limits=agent.limits,
        knowledge_versions=knowledge_versions,
        prompt_versions=prompt_versions,
    )
    return agent, release


def update_agent(*, agent: AIAgent, data: AgentInput) -> AIAgent:
    agent.name = data.name
    agent.model = data.model
    agent.model_params = data.model_params
    agent.allowed_tools = data.allowed_tools
    agent.limits = _normalize_limits(data.limits)
    agent.save(update_fields=["name", "model", "model_params", "allowed_tools", "limits", "updated_at"])
    return agent


def set_agent_active(*, agent: AIAgent, is_active: bool) -> AIAgent:
    agent.is_active = is_active
    agent.save(update_fields=["is_active", "updated_at"])
    return agent
