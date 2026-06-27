from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from hub_platform.ai.models import (
    ChannelAIRelease,
    DocumentScope,
    DocumentStatus,
    KnowledgeDocumentVersion,
    PromptDocumentVersion,
    ReleaseKnowledgeVersion,
    ReleasePromptVersion,
    ReleaseStatus,
)


def _next_version(channel) -> int:
    last = ChannelAIRelease.objects.filter(channel=channel).order_by("-version").first()
    return last.version + 1 if last is not None else 1


def _channel_scope_filter(channel) -> Q:
    # Документы канала: глобальные + относящиеся к продукту канала (если он есть).
    scope = Q(document__scope=DocumentScope.GLOBAL)
    if channel.product_id:
        scope |= Q(document__product_id=channel.product_id)
    return scope


@transaction.atomic
def _create_release(*, channel, author, model, model_params, allowed_tools, limits, retrieval_index_version, notes, knowledge_versions, prompt_versions) -> ChannelAIRelease:
    release = ChannelAIRelease.objects.create(
        channel=channel,
        version=_next_version(channel),
        status=ReleaseStatus.DRAFT,
        model=model,
        model_params=model_params,
        allowed_tools=allowed_tools,
        limits=limits,
        retrieval_index_version=retrieval_index_version,
        notes=notes,
        created_by=author,
    )
    ReleaseKnowledgeVersion.objects.bulk_create(
        [ReleaseKnowledgeVersion(release=release, knowledge_version=version) for version in knowledge_versions]
    )
    ReleasePromptVersion.objects.bulk_create(
        [ReleasePromptVersion(release=release, prompt_version=version) for version in prompt_versions]
    )
    return release


def create_draft_release(*, channel, author, notes: str = "") -> ChannelAIRelease:
    # Снимок текущей конфигурации агента канала + опубликованных версий включённых документов.
    agent = channel.ai_agent
    organization_id = channel.organization_id
    knowledge_versions = KnowledgeDocumentVersion.objects.filter(
        _channel_scope_filter(channel),
        document__organization_id=organization_id,
        document__is_enabled=True,
        status=DocumentStatus.PUBLISHED,
    )
    prompt_versions = PromptDocumentVersion.objects.filter(
        _channel_scope_filter(channel),
        document__organization_id=organization_id,
        document__is_enabled=True,
        status=DocumentStatus.PUBLISHED,
    )
    return _create_release(
        channel=channel,
        author=author,
        model=agent.model,
        model_params=agent.model_params,
        allowed_tools=agent.allowed_tools,
        limits=agent.limits,
        retrieval_index_version="",
        notes=notes,
        knowledge_versions=list(knowledge_versions),
        prompt_versions=list(prompt_versions),
    )


def create_initial_draft_release(*, channel, author, model, model_params, allowed_tools, limits, knowledge_versions, prompt_versions) -> ChannelAIRelease:
    return _create_release(
        channel=channel,
        author=author,
        model=model,
        model_params=model_params,
        allowed_tools=allowed_tools,
        limits=limits,
        retrieval_index_version="",
        notes="Первая версия агента",
        knowledge_versions=knowledge_versions,
        prompt_versions=prompt_versions,
    )


@transaction.atomic
def publish_release(*, release: ChannelAIRelease) -> ChannelAIRelease:
    ChannelAIRelease.objects.filter(channel=release.channel, status=ReleaseStatus.PUBLISHED).exclude(
        pk=release.pk
    ).update(status=ReleaseStatus.ARCHIVED, published_at=timezone.now())
    release.status = ReleaseStatus.PUBLISHED
    release.published_at = timezone.now()
    release.save(update_fields=["status", "published_at"])
    return release


def rollback_to_release(*, channel, source: ChannelAIRelease, author) -> ChannelAIRelease:
    # Откат создаёт новый черновик из снимка старого release (ADR-HUB-0007).
    return _create_release(
        channel=channel,
        author=author,
        model=source.model,
        model_params=source.model_params,
        allowed_tools=source.allowed_tools,
        limits=source.limits,
        retrieval_index_version=source.retrieval_index_version,
        notes=f"Откат к версии v{source.version}",
        knowledge_versions=[link.knowledge_version for link in source.knowledge_versions.all()],
        prompt_versions=[link.prompt_version for link in source.prompt_versions.all()],
    )
