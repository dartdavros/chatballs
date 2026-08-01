from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Q
from pgvector.django import CosineDistance

from hub_platform.ai.agent_knowledge import (
    runtime_knowledge_for_agent,
    runtime_portal_articles_for_agent,
)
from hub_platform.ai.invocation import embed_texts
from hub_platform.ai.models import AIAgent, KnowledgeFragment
from hub_platform.ai.provider.base import ProviderError


def _agent_fragments(agent: AIAgent):
    # Оба источника знаний агента живут в одной таблице фрагментов, поэтому
    # поиск остаётся одним запросом (ADR-HUB-0016).
    return KnowledgeFragment.objects.filter(
        Q(knowledge_id__in=runtime_knowledge_for_agent(agent).values("id"))
        | Q(portal_article_id__in=runtime_portal_articles_for_agent(agent).values("id"))
    ).select_related("knowledge", "portal_article__published_revision")


def lexical_search(agent: AIAgent, query: str, *, limit: int = 5) -> list[KnowledgeFragment]:
    if not query.strip():
        return []
    search_query = SearchQuery(query, search_type="websearch")
    return list(
        _agent_fragments(agent)
        .annotate(rank=SearchRank(SearchVector("content"), search_query))
        .filter(rank__gt=0)
        .order_by("-rank")[:limit]
    )


def semantic_search(
    agent: AIAgent, query_vector: list[float], *, limit: int = 5
) -> list[KnowledgeFragment]:
    return list(
        _agent_fragments(agent)
        .filter(embedding__isnull=False)
        .order_by(CosineDistance("embedding", query_vector))[:limit]
    )


class KnowledgeRetriever:
    """Hybrid retriever: semantic (pgvector) primary, lexical (Postgres FTS) complementary."""

    def retrieve(self, *, agent: AIAgent, query: str, limit: int = 5) -> list[KnowledgeFragment]:
        # Семантический поиск опционален: если провайдер не даёт эмбеддинги —
        # работаем на лексическом (Postgres FTS), не падая.
        try:
            query_vector = embed_texts(
                channel=agent.channel,
                texts=[query],
                model=settings.CUS_AI_EMBEDDING_MODEL,
                purpose="retrieval_query",
            )[0].vector
            semantic = semantic_search(agent, query_vector, limit=limit)
        except ProviderError:
            semantic = []
        lexical = lexical_search(agent, query, limit=limit)
        seen = {fragment.id for fragment in semantic}
        merged = semantic + [fragment for fragment in lexical if fragment.id not in seen]
        return merged[:limit]
