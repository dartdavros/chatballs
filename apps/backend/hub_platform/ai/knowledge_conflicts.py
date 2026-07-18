from collections.abc import Iterable
from dataclasses import dataclass

from django.db.models import Q

from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.models import AIAgent, AIAgentStatus, Knowledge
from hub_platform.channels.models import Channel


@dataclass(frozen=True, slots=True)
class AgentKnowledgeConflict:
    agent_id: int
    agent_name: str
    knowledge_id: int
    knowledge_title: str

    def payload(self) -> dict[str, object]:
        return {
            "agent": {"id": self.agent_id, "name": self.agent_name},
            "knowledge": {
                "id": self.knowledge_id,
                "title": self.knowledge_title,
            },
        }


class KnowledgeScopeConflict(Exception):
    code = "agent_knowledge_scope_conflict"

    def __init__(self, conflicts: Iterable[AgentKnowledgeConflict]) -> None:
        self.conflicts = tuple(
            sorted(
                conflicts,
                key=lambda item: (item.agent_id, item.knowledge_id),
            )
        )
        super().__init__("Knowledge scope conflicts with assigned agents")

    def payload(self) -> dict[str, object]:
        return {
            "code": self.code,
            "detail": str(self),
            "conflicts": [conflict.payload() for conflict in self.conflicts],
        }


def _active_agents():
    return AIAgent.objects.exclude(status=AIAgentStatus.ARCHIVED)


def require_knowledge_scope_compatible(
    *, knowledge: Knowledge, visibility: str, department_ids: Iterable[int]
) -> None:
    if visibility == KnowledgeVisibility.ORGANIZATION:
        return
    allowed_department_ids = set(department_ids)
    agents = (
        _active_agents()
        .filter(knowledge_items=knowledge)
        .filter(
            Q(channel__department_id__isnull=True)
            | ~Q(channel__department_id__in=allowed_department_ids)
        )
        .order_by("id")
    )
    conflicts = [
        AgentKnowledgeConflict(
            agent_id=agent.id,
            agent_name=agent.name,
            knowledge_id=knowledge.id,
            knowledge_title=knowledge.title,
        )
        for agent in agents
    ]
    if conflicts:
        raise KnowledgeScopeConflict(conflicts)


def require_channel_department_compatible(*, channel: Channel, department_id: int | None) -> None:
    agent = _active_agents().filter(channel=channel).prefetch_related("knowledge_items").first()
    if agent is None:
        return
    incompatible = agent.knowledge_items.filter(visibility=KnowledgeVisibility.DEPARTMENTS)
    if department_id is not None:
        compatible_ids = incompatible.filter(department_links__department_id=department_id).values(
            "id"
        )
        incompatible = incompatible.exclude(id__in=compatible_ids)
    conflicts = [
        AgentKnowledgeConflict(
            agent_id=agent.id,
            agent_name=agent.name,
            knowledge_id=knowledge.id,
            knowledge_title=knowledge.title,
        )
        for knowledge in incompatible.order_by("id")
    ]
    if conflicts:
        raise KnowledgeScopeConflict(conflicts)
