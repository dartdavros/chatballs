from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from hub_platform.ai.extraction import extract_text
from hub_platform.ai.indexing import reindex_knowledge
from hub_platform.ai.models import AIAgent, AIAgentStatus, Knowledge, KnowledgeAttachment
from hub_platform.channels.models import Channel
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.storage import adjust_storage_usage
from hub_platform.tenancy.storage_quota import (
    finalize_storage,
    release_storage,
    reserve_storage,
)


@dataclass(frozen=True)
class AgentInput:
    name: str
    model: str
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
    model: str
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
        status=AIAgentStatus.DRAFT,
        model=data.model,
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
    agent.model = data.model
    agent.model_params = data.model_params
    agent.allowed_tools = data.allowed_tools
    agent.limits = _normalize_limits(data.limits)
    agent.persona = data.persona
    agent.tone = data.tone
    agent.instructions = data.instructions
    agent.save(update_fields=["name", "model", "model_params", "allowed_tools", "limits", "persona", "tone", "instructions", "updated_at"])
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


# --- Знания (ADR-HUB-0023) ---


@dataclass(frozen=True)
class KnowledgeInput:
    title: str
    description: str
    content: str
    is_enabled: bool


def create_knowledge(*, context: TenantContext, data: KnowledgeInput) -> Knowledge:
    if not data.title.strip():
        raise ValidationError({"title": "Title is required"})
    knowledge = Knowledge.objects.create(
        organization=context.organization,
        title=data.title.strip(),
        description=data.description.strip(),
        content=data.content,
        is_enabled=data.is_enabled,
    )
    reindex_knowledge(knowledge)
    return knowledge


def update_knowledge(*, context: TenantContext, knowledge: Knowledge, data: KnowledgeInput) -> Knowledge:
    if knowledge.organization_id != context.organization_id:
        raise ValidationError({"knowledge": "Knowledge belongs to another organization"})
    if not data.title.strip():
        raise ValidationError({"title": "Title is required"})
    content_changed = knowledge.content != data.content
    knowledge.title = data.title.strip()
    knowledge.description = data.description.strip()
    knowledge.content = data.content
    knowledge.is_enabled = data.is_enabled
    knowledge.save(update_fields=["title", "description", "content", "is_enabled", "updated_at"])
    if content_changed:
        reindex_knowledge(knowledge)
    return knowledge


def delete_knowledge(*, context: TenantContext, knowledge: Knowledge) -> None:
    if knowledge.organization_id != context.organization_id:
        raise ValidationError({"knowledge": "Knowledge belongs to another organization"})
    # Файлы вложений удаляются вместе со знанием: сначала с диска, потом запись.
    attachments = list(knowledge.attachments.all())
    released_bytes = sum(attachment.size for attachment in attachments)
    for attachment in attachments:
        attachment.file.delete(save=False)
    knowledge.delete()
    if released_bytes:
        adjust_storage_usage(context=context, delta_bytes=-released_bytes)


_MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


@transaction.atomic
def add_attachment(
    *, context: TenantContext, knowledge: Knowledge, upload: UploadedFile
) -> KnowledgeAttachment:
    if knowledge.organization_id != context.organization_id:
        raise ValidationError({"knowledge": "Knowledge belongs to another organization"})
    original_name = (upload.name or "").strip()
    if not original_name:
        raise ValidationError({"file": "File name is required"})
    if upload.size and upload.size > _MAX_ATTACHMENT_BYTES:
        raise ValidationError({"file": "File is too large (max 25 MB)"})
    # Повторная загрузка с тем же именем заменяет файл (ADR-HUB-0023: без версий).
    existing = knowledge.attachments.filter(original_name=original_name).first()
    existing_size = existing.size if existing is not None else 0
    data = upload.read()
    # C07 storage gate (SPEC §10): reserve the expected size before the write so a
    # concurrent upload cannot exceed storage_bytes; finalize with the actual size
    # after the object is persisted, or release on failure. Reads are never gated.
    # Deterministic key makes a retried upload of the same file idempotent; a prior
    # finalized/released reservation is ignored by the active-reservation filter.
    reservation_key = f"attachment:{knowledge.id}:{original_name}"
    reserve_storage(
        context=context, expected_bytes=len(data), idempotency_key=reservation_key
    )
    try:
        if existing is not None:
            existing.file.delete(save=False)
            existing.delete()
            if existing_size:
                adjust_storage_usage(context=context, delta_bytes=-existing_size)
        content_type = upload.content_type or ""
        attachment = KnowledgeAttachment(
            organization=context.organization,
            knowledge=knowledge,
            original_name=original_name,
            content_type=content_type,
            size=len(data),
            extracted_text=extract_text(
                filename=original_name, content_type=content_type, data=data
            ),
        )
        from django.core.files.base import ContentFile

        attachment.file.save(original_name, ContentFile(data), save=True)
    except Exception:
        # Upload failed after reservation: release the reserved bytes (SPEC §10.4).
        release_storage(context=context, idempotency_key=reservation_key)
        raise
    finalize_storage(
        context=context, idempotency_key=reservation_key, actual_bytes=len(data)
    )
    reindex_knowledge(knowledge)
    return attachment


def delete_attachment(*, context: TenantContext, attachment: KnowledgeAttachment) -> None:
    if attachment.knowledge.organization_id != context.organization_id:
        raise ValidationError({"attachment": "Attachment belongs to another organization"})
    knowledge = attachment.knowledge
    released_bytes = attachment.size
    attachment.file.delete(save=False)
    attachment.delete()
    if released_bytes:
        adjust_storage_usage(context=context, delta_bytes=-released_bytes)
    reindex_knowledge(knowledge)
