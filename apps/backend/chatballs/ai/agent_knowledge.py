from django.db.models import QuerySet

from chatballs.ai.models import AIAgent, Knowledge
from chatballs.channels.models import Channel
from chatballs.support_portals.models import PortalArticle
from chatballs.support_portals.statuses import ArticleStatus, PortalStatus

# Библиотека знаний — общая для организации (ADR-CHATBALLS-0041 §8): агент использует
# только явно выбранные и включённые знания, областей видимости нет.


def knowledge_available_to_channel(
    queryset: QuerySet[Knowledge], *, channel: Channel
) -> QuerySet[Knowledge]:
    return queryset.filter(organization_id=channel.organization_id)


def portal_articles_available_to_channel(
    queryset: QuerySet[PortalArticle], *, channel: Channel
) -> QuerySet[PortalArticle]:
    return queryset.filter(organization_id=channel.organization_id)


def runtime_knowledge_for_agent(agent: AIAgent) -> QuerySet[Knowledge]:
    """Явно выбранные и включённые знания агента."""
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
