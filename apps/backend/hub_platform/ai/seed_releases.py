from __future__ import annotations

from django.db import transaction

from hub_platform.ai.models import (
    AIAgent,
    ChannelAIRelease,
    DocumentScope,
    DocumentStatus,
    KnowledgeDocumentVersion,
    PromptDocumentVersion,
    ReleaseKnowledgeVersion,
    ReleasePromptVersion,
    ReleaseStatus,
)
from hub_platform.ai.releases import publish_release
from hub_platform.channels.models import DEFAULT_CHANNEL_MODEL, Channel
from hub_platform.identity.models import HumanUser, Organization


def _release_version_ids(release: ChannelAIRelease) -> tuple[set[int], set[int]]:
    knowledge_ids = {link.knowledge_version_id for link in release.knowledge_versions.all()}
    prompt_ids = {link.prompt_version_id for link in release.prompt_versions.all()}
    return knowledge_ids, prompt_ids


def _next_release_version(channel: Channel) -> int:
    latest = ChannelAIRelease.objects.filter(channel=channel).order_by("-version").first()
    return latest.version + 1 if latest else 1


def _published_knowledge_versions(channel: Channel) -> list[KnowledgeDocumentVersion]:
    queryset = KnowledgeDocumentVersion.objects.filter(
        document__organization=channel.organization,
        document__is_enabled=True,
        status=DocumentStatus.PUBLISHED,
    )
    if channel.product_id:
        queryset = queryset.filter(document__scope=DocumentScope.GLOBAL) | queryset.filter(
            document__product=channel.product
        )
    else:
        queryset = queryset.filter(document__scope=DocumentScope.GLOBAL)
    return list(queryset.distinct().order_by("document__code", "-version"))


def _published_prompt_versions(channel: Channel) -> list[PromptDocumentVersion]:
    queryset = PromptDocumentVersion.objects.filter(
        document__organization=channel.organization,
        document__is_enabled=True,
        status=DocumentStatus.PUBLISHED,
    )
    if channel.product_id:
        queryset = queryset.filter(document__scope=DocumentScope.GLOBAL) | queryset.filter(
            document__product=channel.product
        )
    else:
        queryset = queryset.filter(document__scope=DocumentScope.GLOBAL)
    selected: dict[str, PromptDocumentVersion] = {}
    for version in (
        queryset.select_related("document").distinct().order_by("document__category", "-version")
    ):
        category = version.document.category
        current = selected.get(category)
        if current is None:
            selected[category] = version
            continue
        current_priority = int(bool(current.document.product_id))
        candidate_priority = int(bool(version.document.product_id))
        if (candidate_priority, version.version) > (current_priority, current.version):
            selected[category] = version
    return list(selected.values())


@transaction.atomic
def _create_release_snapshot(
    *, channel: Channel, agent: AIAgent, author: HumanUser | None
) -> ChannelAIRelease:
    release = ChannelAIRelease.objects.create(
        channel=channel,
        version=_next_release_version(channel),
        status=ReleaseStatus.DRAFT,
        model=agent.model,
        model_params=agent.model_params,
        allowed_tools=agent.allowed_tools,
        limits=agent.limits,
        retrieval_index_version="",
        notes="Production seed release",
        created_by=author,
    )
    ReleaseKnowledgeVersion.objects.bulk_create(
        [
            ReleaseKnowledgeVersion(release=release, knowledge_version=version)
            for version in _published_knowledge_versions(channel)
        ]
    )
    ReleasePromptVersion.objects.bulk_create(
        [
            ReleasePromptVersion(release=release, prompt_version=version)
            for version in _published_prompt_versions(channel)
        ]
    )
    return release


def ensure_agents_and_releases(
    *, organization: Organization, author: HumanUser | None
) -> tuple[int, int]:
    agents_created = 0
    releases_created = 0
    for channel in Channel.objects.filter(organization=organization).order_by("code"):
        agent, agent_created = AIAgent.objects.update_or_create(
            channel=channel,
            defaults={
                "name": f"{channel.name} Agent",
                "is_active": True,
                "model": channel.model or DEFAULT_CHANNEL_MODEL,
            },
        )
        agents_created += int(agent_created)
        draft = _create_release_snapshot(channel=channel, agent=agent, author=author)
        desired = _release_version_ids(draft)
        current = (
            ChannelAIRelease.objects.filter(channel=channel, status=ReleaseStatus.PUBLISHED)
            .prefetch_related("knowledge_versions", "prompt_versions")
            .order_by("-version")
            .first()
        )
        if current and current.model == agent.model and _release_version_ids(current) == desired:
            draft.delete()
            continue
        publish_release(release=draft)
        releases_created += 1
    return agents_created, releases_created
