from django.db.models import Q, QuerySet

from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.models import AIAgent, Knowledge
from hub_platform.channels.models import Channel
from hub_platform.support_portals.models import PortalArticle
from hub_platform.support_portals.statuses import ArticleStatus, PortalStatus


def knowledge_available_to_channel(
    queryset: QuerySet[Knowledge], *, channel: Channel
) -> QuerySet[Knowledge]:
    """Apply the single department-availability predicate for an agent channel."""
    queryset = queryset.filter(organization_id=channel.organization_id)
    if channel.department_id is None:
        return queryset.filter(visibility=KnowledgeVisibility.ORGANIZATION)
    return queryset.filter(
        Q(visibility=KnowledgeVisibility.ORGANIZATION)
        | Q(
            visibility=KnowledgeVisibility.DEPARTMENTS,
            department_links__department_id=channel.department_id,
        )
    ).distinct()


def portal_articles_available_to_channel(
    queryset: QuerySet[PortalArticle], *, channel: Channel
) -> QuerySet[PortalArticle]:
    """Статьи портала доступны агенту канала того же отдела.

    Портал по определению живёт в отделе поддержки, поэтому агент вне этого
    отдела статьи не получает — то же правило отделовой доступности, что и у
    знаний библиотеки (ADR-HUB-0036).
    """
    queryset = queryset.filter(organization_id=channel.organization_id)
    if channel.department_id is None:
        return queryset.none()
    return queryset.filter(portal__department_id=channel.department_id)


def runtime_knowledge_for_agent(agent: AIAgent) -> QuerySet[Knowledge]:
    """Return explicitly selected, department-compatible, enabled knowledge."""
    selected = Knowledge.objects.filter(agents=agent, is_enabled=True)
    return knowledge_available_to_channel(selected, channel=agent.channel)


def runtime_portal_articles_for_agent(agent: AIAgent) -> QuerySet[PortalArticle]:
    """Прикреплённые статьи, доступные агенту прямо сейчас: опубликованные и
    на неархивном портале. Черновики и архив в ответы агента не попадают."""
    selected = (
        PortalArticle.objects.filter(
            agents=agent,
            status=ArticleStatus.PUBLISHED,
            published_revision__isnull=False,
        )
        .exclude(portal__status=PortalStatus.ARCHIVED)
    )
    return portal_articles_available_to_channel(selected, channel=agent.channel)
