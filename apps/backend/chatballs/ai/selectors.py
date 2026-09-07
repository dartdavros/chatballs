from collections.abc import Sequence
from dataclasses import dataclass

from django.db.models import Count, Prefetch, Q, QuerySet

from chatballs.ai.agent_knowledge import knowledge_available_to_channel
from chatballs.ai.knowledge_policy import readable_knowledge, writable_knowledge
from chatballs.ai.models import AIAgent, Knowledge, KnowledgeCategory
from chatballs.channels.models import Channel
from chatballs.identity.models import AuditEvent
from chatballs.identity.policy import has_capability_any_scope
from chatballs.tenancy.context import TenantContext

KNOWLEDGE_EDIT_ACTIONS = ("ai.knowledge_created", "ai.knowledge_updated")


def knowledge_editors(
    *, organization_id: int, knowledge_ids: Sequence[int]
) -> dict[int, str]:
    """Кто последним правил каждое знание — подпись под датой в колонке
    «Обновлено» (дизайн-базлайн v2, кадр KB1). Один запрос на весь список:
    события создания и правки уже пишутся в журнал."""
    if not knowledge_ids:
        return {}
    events = (
        AuditEvent.objects.filter(
            organization_id=organization_id,
            action__in=KNOWLEDGE_EDIT_ACTIONS,
            object_type="Knowledge",
            object_id__in=[str(knowledge_id) for knowledge_id in knowledge_ids],
        )
        .select_related("actor")
        .order_by("object_id", "-created_at")
    )
    editors: dict[int, str] = {}
    for event in events:
        if event.actor is None:
            continue
        try:
            knowledge_id = int(event.object_id)
        except (TypeError, ValueError):
            continue
        editors.setdefault(knowledge_id, event.actor.full_name or event.actor.email)
    return editors


def agents_for_context(context: TenantContext) -> QuerySet[AIAgent]:
    return (
        AIAgent.objects.select_related("channel", "channel__group")
        .prefetch_related(
            "knowledge_items",
            "portal_articles__portal",
            "portal_articles__published_revision",
        )
        .filter(channel__organization_id=context.organization_id)
        .order_by("channel__name")
    )


def agent_for_context(*, context: TenantContext, agent_id: int) -> AIAgent:
    return agents_for_context(context).get(id=agent_id)


def agents_for_employee(*, context: TenantContext, capability: str) -> QuerySet[AIAgent]:
    queryset = agents_for_context(context)
    if has_capability_any_scope(context.membership, capability):
        return queryset
    return queryset.none()


def agent_for_employee(*, context: TenantContext, agent_id: int, capability: str) -> AIAgent:
    return agents_for_employee(context=context, capability=capability).get(id=agent_id)


def knowledge_for_context(context: TenantContext) -> QuerySet[Knowledge]:
    return knowledge_for_employee(context=context)


def _knowledge_base(context: TenantContext) -> QuerySet[Knowledge]:
    return Knowledge.objects.filter(organization_id=context.organization_id)


def _with_knowledge_relations(queryset: QuerySet[Knowledge]) -> QuerySet[Knowledge]:
    return (
        queryset.select_related("category")
        .prefetch_related("attachments")
        .annotate(
            agents_count=Count("agents", distinct=True),
            fragments_count=Count("fragments", distinct=True),
        )
        .order_by("title")
    )


def knowledge_for_employee(
    *, context: TenantContext, capability: str = "ai.view"
) -> QuerySet[Knowledge]:
    return _with_knowledge_relations(
        readable_knowledge(
            context=context,
            queryset=_knowledge_base(context),
            capability=capability,
        )
    )


def writable_knowledge_for_employee(*, context: TenantContext) -> QuerySet[Knowledge]:
    return _with_knowledge_relations(
        writable_knowledge(context=context, queryset=_knowledge_base(context))
    )


def knowledge_item_for_context(*, context: TenantContext, knowledge_id: int) -> Knowledge:
    return knowledge_for_employee(context=context).get(id=knowledge_id)


def writable_knowledge_item_for_employee(*, context: TenantContext, knowledge_id: int) -> Knowledge:
    return writable_knowledge_for_employee(context=context).get(id=knowledge_id)


def knowledge_available_to_agent(*, agent: AIAgent) -> QuerySet[Knowledge]:
    queryset = knowledge_available_to_channel(
        _with_knowledge_relations(
            Knowledge.objects.filter(
                organization_id=agent.channel.organization_id,
            )
        ),
        channel=agent.channel,
    )
    return queryset


def category_tree_for_employee(*, context: TenantContext) -> list[KnowledgeCategory]:
    available_ids = readable_knowledge(
        context=context,
        queryset=_knowledge_base(context),
    ).values("id")
    categories = list(
        KnowledgeCategory.objects.filter(organization_id=context.organization_id)
        .select_related("parent")
        .annotate(
            direct_knowledge_count=Count(
                "knowledge_items",
                filter=Q(knowledge_items__id__in=available_ids),
                distinct=True,
            )
        )
        .order_by("sort_order", "name", "id")
    )
    children_by_parent: dict[int | None, list[KnowledgeCategory]] = {}
    for category in categories:
        children_by_parent.setdefault(category.parent_id, []).append(category)

    ordered: list[KnowledgeCategory] = []
    pending = list(reversed(children_by_parent.get(None, [])))
    while pending:
        category = pending.pop()
        ordered.append(category)
        pending.extend(reversed(children_by_parent.get(category.id, [])))

    subtree_counts: dict[int, int] = {}
    for category in reversed(ordered):
        count = category.direct_knowledge_count + sum(
            subtree_counts[child.id] for child in children_by_parent.get(category.id, [])
        )
        category.knowledge_count = count
        subtree_counts[category.id] = count
    return ordered


@dataclass(frozen=True, slots=True)
class KnowledgeFilters:
    category_id: int | None = None
    is_enabled: bool | None = None
    search: str = ""


def apply_knowledge_filters(
    queryset: QuerySet[Knowledge], filters: KnowledgeFilters
) -> QuerySet[Knowledge]:
    if filters.category_id is not None:
        queryset = queryset.filter(category_id=filters.category_id)
    if filters.is_enabled is not None:
        queryset = queryset.filter(is_enabled=filters.is_enabled)
    search = filters.search.strip()
    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))
    return queryset.distinct()
