"""Каналы, интеграции, AI-агенты, база знаний (со вложениями), учёт LLM."""

from __future__ import annotations

from django.core.files.base import ContentFile

from hub_platform.ai.models import (
    AIAgent,
    AIAgentStatus,
    Knowledge,
    KnowledgeAttachment,
    LlmInvocation,
    LlmInvocationStatus,
)
from hub_platform.channels.models import Channel
from hub_platform.identity.demo_seed import manifest
from hub_platform.identity.demo_seed.refs import DemoRefs
from hub_platform.integrations.models import Integration, IntegrationKind, IntegrationStatus
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.storage_quota import finalize_storage, reserve_storage


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("channels_ai")
    organization = refs.organization

    for item in data["integrations"]:
        channel = refs.channels.get(item.get("channel"))
        integration, _ = Integration.objects.get_or_create(
            organization=organization,
            provider=item["provider"],
            name=item["name"],
            defaults={
                "kind": item.get("kind", IntegrationKind.MESSENGER),
                "channel": channel,
                "status": item.get("status", IntegrationStatus.OK),
                "config": item.get("config", {}),
            },
        )
        refs.integrations[item["key"]] = integration

    for item in data["channels"]:
        _ensure_channel(refs, item)

    for item in data.get("agents", []):
        _ensure_agent(refs, item)

    _ensure_knowledge(context, refs, data.get("knowledge", []))

    for item in data.get("llmInvocations", []):
        _ensure_llm_invocation(refs, item)


def _ensure_channel(refs: DemoRefs, item: dict) -> None:
    channel, _ = Channel.objects.get_or_create(
        organization=refs.organization,
        code=item["code"],
        defaults={
            "name": item["name"],
            "group": refs.groups.get(item.get("group")),
            "product": refs.products.get(item.get("product")),
            "provider_integration": refs.integrations.get(item.get("providerIntegration")),
            "is_active": item.get("isActive", True),
            **item.get("policy", {}),
        },
    )
    refs.channels[item["code"]] = channel


def _ensure_agent(refs: DemoRefs, item: dict) -> None:
    channel = refs.channels[item["channel"]]
    agent, created = AIAgent.objects.get_or_create(
        channel=channel,
        defaults={
            "name": item["name"],
            "status": item.get("status", AIAgentStatus.ACTIVE),
            "model": item.get("model", ""),
            "persona": item.get("persona", ""),
            "tone": item.get("tone", ""),
            "instructions": item.get("instructions", ""),
        },
    )
    if created:
        for knowledge_key in item.get("knowledge", []):
            knowledge = refs.knowledge.get(knowledge_key)
            if knowledge is not None:
                agent.knowledge_items.add(knowledge)


def _ensure_knowledge(context: TenantContext, refs: DemoRefs, items: list[dict]) -> None:
    organization = refs.organization
    # Системная категория «Без категории» создаётся в foundation; хелпер
    # идемпотентен, поэтому безопасно получить её здесь же.
    from hub_platform.ai.knowledge_categories import ensure_uncategorized_category

    category = ensure_uncategorized_category(organization)

    for item in items:
        knowledge, created = Knowledge.objects.get_or_create(
            organization=organization,
            title=item["title"],
            defaults={
                "category": category,
                "description": item.get("description", ""),
                "content": item.get("content", ""),
            },
        )
        refs.knowledge[item["key"]] = knowledge
        if created:
            for attachment_key in item.get("attachments", []):
                _attach_knowledge_file(context, refs, knowledge, attachment_key)


def _attach_knowledge_file(
    context: TenantContext, refs: DemoRefs, knowledge: Knowledge, filename: str
) -> None:
    if KnowledgeAttachment.objects.filter(knowledge=knowledge, original_name=filename).exists():
        return
    data = manifest.media_text(filename).encode("utf-8")
    reservation_key = f"demo-knowledge:{knowledge.id}:{filename}"
    reserve_storage(context=context, expected_bytes=len(data), idempotency_key=reservation_key)
    suffix = filename.rsplit(".", 1)[-1].lower()
    content_type = "text/markdown" if suffix == "md" else "application/octet-stream"
    attachment = KnowledgeAttachment.objects.create(
        organization=refs.organization,
        knowledge=knowledge,
        original_name=filename,
        content_type=content_type,
        size=len(data),
        extracted_text=manifest.media_text(filename),
    )
    attachment.file.save(filename, ContentFile(data), save=True)
    finalize_storage(context=context, idempotency_key=reservation_key, actual_bytes=len(data))


def _ensure_llm_invocation(refs: DemoRefs, item: dict) -> None:
    channel = refs.channels[item["channel"]]
    product = refs.products.get(item.get("product"))
    prompt_tokens = item.get("promptTokens", 0)
    completion_tokens = item.get("completionTokens", 0)
    LlmInvocation.objects.get_or_create(
        channel=channel,
        purpose=item["purpose"],
        operation=item.get("operation", "chat"),
        model=item.get("model", ""),
        defaults={
            "product": product,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_micros": item.get("costMicros", 0),
            "status": item.get("status", LlmInvocationStatus.SUCCESS),
        },
    )
