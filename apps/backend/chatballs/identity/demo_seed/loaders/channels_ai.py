"""Агенты (карточки Channel+AIAgent), подключения, LLM-провайдер, знания, учёт LLM."""

from __future__ import annotations

from datetime import timedelta

from django.core.files.base import ContentFile

from chatballs.ai.agent_card import ensure_channel_agent
from chatballs.ai.knowledge_categories import create_category, ensure_uncategorized_category
from chatballs.ai.knowledge_services import KnowledgeInput, create_knowledge
from chatballs.ai.models import (
    AIAgent,
    KnowledgeAttachment,
    LlmInvocation,
    LlmInvocationStatus,
)
from chatballs.channels.models import Channel
from chatballs.identity.audit import record_audit_event
from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.loaders.common import backdate, now, rng
from chatballs.identity.demo_seed.refs import DemoRefs
from chatballs.integrations.models import Integration, IntegrationKind, IntegrationStatus
from chatballs.integrations.services import IntegrationInput, create_integration
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.storage_quota import finalize_storage, reserve_storage
from chatballs.webchat.widgets import ensure_widget


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("channels_ai", refs.language)
    current = now()

    llm = _ensure_llm_provider(context, refs, data["llmProvider"], current)
    for item in data["agents"]:
        _ensure_agent(context, refs, item, llm, current)
    for item in data["connections"]:
        _ensure_connection(context, refs, item, current)
    _ensure_categories(context, refs, data.get("knowledgeCategories", []), parent=None)
    for item in data.get("knowledge", []):
        _ensure_knowledge(context, refs, item, current)
    for item in data["agents"]:
        _attach_agent_knowledge(refs, item)
    _generate_usage(refs, data.get("usage"), current)


def _ensure_llm_provider(context: TenantContext, refs: DemoRefs, item: dict, current) -> Integration:
    integration = Integration.objects.filter(
        organization=refs.organization, kind=IntegrationKind.LLM_PROVIDER, name=item["name"]
    ).first()
    if integration is None:
        integration = create_integration(
            context=context,
            data=IntegrationInput(
                provider=item["provider"],
                name=item["name"],
                secret=item.get("secret", ""),
                config=item.get("config", {}),
            ),
        )
        Integration.objects.filter(pk=integration.pk).update(status=item.get("status", IntegrationStatus.UNCHECKED))
        backdate(integration, current - timedelta(days=42))
    refs.integrations[item["key"]] = integration
    return integration


def _ensure_agent(context: TenantContext, refs: DemoRefs, item: dict, llm: Integration, current) -> None:
    organization = refs.organization
    channel, created = Channel.objects.get_or_create(
        organization=organization,
        code=item["code"],
        defaults={
            "name": item["name"],
            "group": refs.groups.get(item.get("group")),
            "is_active": item.get("isActive", True),
            **item.get("policy", {}),
        },
    )
    agent = ensure_channel_agent(channel)
    if created:
        agent.status = item.get("aiStatus", agent.status)
        agent.persona = item.get("persona", "")
        agent.tone = item.get("tone", "")
        agent.instructions = item.get("instructions", "")
        agent.limits = item.get("limits", {})
        if agent.status in ("ACTIVE", "DISABLED"):
            agent.provider_integration = llm
            agent.model = (llm.config or {}).get("default_model", "demo")
        agent.save()
        when = current - timedelta(days=item.get("createdDaysAgo", 30))
        backdate(channel, when, "created_at", "updated_at")
        backdate(agent, when, "created_at", "updated_at")
        record_audit_event(
            organization=organization,
            actor=refs.users.get("anna"),
            action="ai.agent_created",
            object_type="Agent",
            object_id=str(channel.id),
            payload={"name": channel.name, "source": "demo"},
        )
    refs.channels[item["key"]] = channel
    refs.agents[item["key"]] = agent


def _ensure_connection(context: TenantContext, refs: DemoRefs, item: dict, current) -> None:
    organization = refs.organization
    channel = refs.channels.get(item.get("agent"))
    integration = Integration.objects.filter(
        organization=organization, provider=item["provider"], name=item["name"]
    ).first()
    if integration is None:
        integration = create_integration(
            context=context,
            data=IntegrationInput(
                provider=item["provider"],
                name=item["name"],
                secret=item.get("secret", ""),
                config=item.get("config", {}),
            ),
        )
        Integration.objects.filter(pk=integration.pk).update(
            channel=channel,
            status=item.get("status", IntegrationStatus.OK),
            last_error=item.get("lastError", ""),
            last_checked_at=current - timedelta(minutes=7),
        )
        integration.refresh_from_db()
        backdate(integration, current - timedelta(days=item.get("createdDaysAgo", 20)))
        # Веб-виджет создаётся вместе с WEB-подключением, у которого есть канал.
        widget = ensure_widget(integration)
        if widget is not None:
            widget.status = "PUBLISHED"
            widget.allowed_origins = list(item.get("config", {}).get("allowed_origins", []))
            widget.save(update_fields=["status", "allowed_origins", "updated_at"])
            refs.widgets[item["key"]] = widget
        record_audit_event(
            organization=organization,
            actor=refs.users.get("anna"),
            action="channels.connection_bound",
            object_type="Agent",
            object_id=str(channel.id) if channel else "",
            payload={"integrationId": integration.id, "source": "demo"},
        )
    refs.integrations[item["key"]] = integration


def _ensure_categories(context: TenantContext, refs: DemoRefs, items: list[dict], *, parent) -> None:
    from chatballs.ai.knowledge_models import KnowledgeCategory

    for index, item in enumerate(items, start=1):
        category = KnowledgeCategory.objects.filter(
            organization=refs.organization, name=item["name"], parent=parent
        ).first()
        if category is None:
            category = create_category(
                context=context, name=item["name"], parent=parent, sort_order=index
            )
        refs.knowledge_categories[item["key"]] = category
        _ensure_categories(context, refs, item.get("children", []), parent=category)


def _ensure_knowledge(context: TenantContext, refs: DemoRefs, item: dict, current) -> None:
    from chatballs.ai.models import Knowledge

    organization = refs.organization
    knowledge = Knowledge.objects.filter(organization=organization, title=item["title"]).first()
    if knowledge is None:
        category = refs.knowledge_categories.get(item.get("category")) or ensure_uncategorized_category(organization)
        knowledge = create_knowledge(
            context=context,
            data=KnowledgeInput(
                title=item["title"],
                description=item.get("description", ""),
                content=item.get("content", ""),
                is_enabled=item.get("isEnabled", True),
                category_id=category.id,
            ),
        )
        when = current - timedelta(days=item.get("createdDaysAgo", 20))
        backdate(knowledge, when, "created_at", "updated_at")
        for attachment in item.get("attachments", []):
            _attach_knowledge_file(context, refs, knowledge, attachment)
    refs.knowledge[item["key"]] = knowledge


def _attach_knowledge_file(context: TenantContext, refs: DemoRefs, knowledge, spec) -> None:
    if isinstance(spec, str):
        spec = {"file": spec}
    filename = spec["file"]
    if KnowledgeAttachment.objects.filter(knowledge=knowledge, original_name=filename).exists():
        return
    payload = manifest.media_bytes(filename)
    text_source = spec.get("text", filename)
    extracted_text = manifest.media_text(text_source) if text_source.rsplit(".", 1)[-1] in ("md", "txt") else ""
    suffix = filename.rsplit(".", 1)[-1].lower()
    content_type = spec.get("contentType") or {
        "md": "text/markdown",
        "txt": "text/plain",
        "pdf": "application/pdf",
    }.get(suffix, "application/octet-stream")
    reservation_key = f"demo-knowledge:{knowledge.id}:{filename}"
    reserve_storage(context=context, expected_bytes=len(payload), idempotency_key=reservation_key)
    attachment = KnowledgeAttachment.objects.create(
        organization=refs.organization,
        knowledge=knowledge,
        original_name=filename,
        content_type=content_type,
        size=len(payload),
        extracted_text=extracted_text,
    )
    attachment.file.save(filename, ContentFile(payload), save=True)
    finalize_storage(context=context, idempotency_key=reservation_key, actual_bytes=len(payload))
    if extracted_text:
        from chatballs.ai.indexing import reindex_knowledge

        reindex_knowledge(knowledge)


def _attach_agent_knowledge(refs: DemoRefs, item: dict) -> None:
    agent: AIAgent = refs.agents[item["key"]]
    for key in item.get("knowledge", []):
        knowledge = refs.knowledge.get(key)
        if knowledge is not None:
            agent.knowledge_items.add(knowledge)
    # Статьи портала привязываются позже — после загрузчика поддержки (см. support.py).
    refs.agent_article_links[item["key"]] = list(item.get("portalArticles", []))


def _generate_usage(refs: DemoRefs, spec: dict | None, current) -> None:
    """История LlmInvocation за N дней для раздела «Использование AI»."""
    if not spec:
        return
    random = rng()
    if LlmInvocation.objects.filter(channel__organization=refs.organization, purpose="agent_chat").exists():
        return
    failures_left = spec.get("failuresTotal", 0)
    days = spec.get("days", 30)
    for day in range(days, -1, -1):
        day_start = (current - timedelta(days=day)).replace(hour=9, minute=0, second=0, microsecond=0)
        for agent_key, (low, high) in spec.get("chatPerDay", {}).items():
            channel = refs.channels.get(agent_key)
            if channel is None:
                continue
            for _ in range(random.randint(low, high)):
                prompt = random.randint(*spec["promptTokens"])
                completion = random.randint(*spec["completionTokens"])
                failed = failures_left > 0 and random.random() < 0.02
                if failed:
                    failures_left -= 1
                invocation = LlmInvocation.objects.create(
                    channel=channel,
                    purpose="agent_chat",
                    operation="chat",
                    model=spec["model"],
                    prompt_tokens=prompt,
                    completion_tokens=0 if failed else completion,
                    total_tokens=prompt + (0 if failed else completion),
                    cost_micros=0 if failed else int((prompt + completion) * spec["costMicrosPerToken"]),
                    latency_ms=random.randint(900, 4200),
                    status=LlmInvocationStatus.ERROR if failed else LlmInvocationStatus.SUCCESS,
                    error="Provider timeout after 30s" if failed else "",
                )
                backdate(invocation, day_start + timedelta(minutes=random.randint(0, 660)))
        low, high = spec.get("embeddingPerDay", [0, 0])
        channel = refs.channels.get("consultant")
        for _ in range(random.randint(low, high)):
            tokens = random.randint(200, 900)
            invocation = LlmInvocation.objects.create(
                channel=channel,
                purpose="knowledge_index",
                operation="embedding",
                model="text-embedding-3-small",
                prompt_tokens=tokens,
                completion_tokens=0,
                total_tokens=tokens,
                cost_micros=int(tokens * 0.02),
                latency_ms=random.randint(200, 900),
                status=LlmInvocationStatus.SUCCESS,
            )
            backdate(invocation, day_start + timedelta(minutes=random.randint(0, 660)))
