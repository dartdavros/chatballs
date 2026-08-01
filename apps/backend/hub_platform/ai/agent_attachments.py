"""Массовое прикрепление источников знаний к одному агенту.

Обе библиотеки — знания организации и статьи портала поддержки — прикрепляются
по одному правилу: недоступные агенту по отделу элементы не прикрепляются, но и
не роняют операцию, а возвращаются в `skipped_ids`. Так массовое действие над
смешанной выборкой остаётся предсказуемым (SPEC-HUB-0026 §5).
"""

from collections.abc import Iterable
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from hub_platform.ai.agent_knowledge import (
    knowledge_available_to_channel,
    portal_articles_available_to_channel,
)
from hub_platform.ai.knowledge_policy import readable_knowledge
from hub_platform.ai.models import AIAgent, Knowledge
from hub_platform.channels.models import Channel
from hub_platform.support_portals.models import PortalArticle
from hub_platform.tenancy.context import TenantContext


@dataclass(frozen=True, slots=True)
class AgentLinkResult:
    agent_id: int
    # Реально изменённые связи: прикреплённые либо откреплённые за эту операцию.
    linked_ids: tuple[int, ...]
    # Пропущенные: элемент недоступен агенту по отделу.
    skipped_ids: tuple[int, ...]
    selected_ids: tuple[int, ...]


def normalized_ids(raw_ids: Iterable[int], field: str) -> list[int]:
    normalized: list[int] = []
    for value in raw_ids:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValidationError({field: "Positive integer ID required"})
        if value not in normalized:
            normalized.append(value)
    if not normalized:
        raise ValidationError({field: "At least one ID is required"})
    return normalized


def _locked_agent(*, context: TenantContext, agent: AIAgent) -> tuple[AIAgent, Channel]:
    if agent.channel.organization_id != context.organization_id:
        raise ValidationError({"agent": "Agent belongs to another organization"})
    channel = Channel.objects.select_for_update().get(
        id=agent.channel_id,
        organization_id=context.organization_id,
    )
    locked = AIAgent.objects.select_for_update().get(id=agent.id, channel=channel)
    return locked, channel


def _apply(*, manager, requested_ids, available_ids, attach: bool) -> AgentLinkResult:
    current_ids = set(manager.values_list("id", flat=True))
    if attach:
        changed_ids = sorted(available_ids - current_ids)
        skipped_ids = sorted(set(requested_ids) - available_ids)
        if changed_ids:
            manager.add(*changed_ids)
        selected_ids = current_ids | set(changed_ids)
    else:
        # Открепление не требует проверки доступности: снять можно всё, что
        # прикреплено, иначе несовместимую связь стало бы нечем убрать.
        changed_ids = sorted(set(requested_ids) & current_ids)
        skipped_ids = []
        if changed_ids:
            manager.remove(*changed_ids)
        selected_ids = current_ids - set(changed_ids)
    return AgentLinkResult(
        agent_id=manager.instance.id,
        linked_ids=tuple(changed_ids),
        skipped_ids=tuple(skipped_ids),
        selected_ids=tuple(sorted(selected_ids)),
    )


@transaction.atomic
def link_knowledge_to_agent(
    *,
    context: TenantContext,
    agent: AIAgent,
    knowledge_ids: Iterable[int],
    attach: bool,
) -> AgentLinkResult:
    requested_ids = normalized_ids(knowledge_ids, "knowledgeIds")
    locked, channel = _locked_agent(context=context, agent=agent)
    readable = readable_knowledge(
        context=context,
        queryset=Knowledge.objects.filter(
            organization_id=context.organization_id,
            id__in=requested_ids,
        ),
    )
    found_ids = set(readable.values_list("id", flat=True))
    if len(found_ids) != len(requested_ids):
        raise ValidationError({"knowledgeIds": "Unknown knowledge item"})
    available_ids = set(
        knowledge_available_to_channel(
            Knowledge.objects.filter(id__in=found_ids),
            channel=channel,
        ).values_list("id", flat=True)
    )
    return _apply(
        manager=locked.knowledge_items,
        requested_ids=requested_ids,
        available_ids=available_ids,
        attach=attach,
    )


@transaction.atomic
def link_portal_articles_to_agent(
    *,
    context: TenantContext,
    agent: AIAgent,
    article_ids: Iterable[int],
    attach: bool,
) -> AgentLinkResult:
    requested_ids = normalized_ids(article_ids, "articleIds")
    locked, channel = _locked_agent(context=context, agent=agent)
    articles = PortalArticle.objects.filter(
        organization_id=context.organization_id,
        id__in=requested_ids,
    )
    found_ids = set(articles.values_list("id", flat=True))
    if len(found_ids) != len(requested_ids):
        raise ValidationError({"articleIds": "Unknown portal article"})
    available_ids = set(
        portal_articles_available_to_channel(
            PortalArticle.objects.filter(id__in=found_ids),
            channel=channel,
        ).values_list("id", flat=True)
    )
    return _apply(
        manager=locked.portal_articles,
        requested_ids=requested_ids,
        available_ids=available_ids,
        attach=attach,
    )
