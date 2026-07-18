from django.db.models import Q, QuerySet

from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.models import AIAgent, Knowledge
from hub_platform.channels.models import Channel


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


def runtime_knowledge_for_agent(agent: AIAgent) -> QuerySet[Knowledge]:
    """Return explicitly selected, department-compatible, enabled knowledge."""
    selected = Knowledge.objects.filter(agents=agent, is_enabled=True)
    return knowledge_available_to_channel(selected, channel=agent.channel)
