from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from pgvector.django import CosineDistance

from hub_platform.ai.invocation import embed_texts
from hub_platform.ai.models import ChannelAIRelease, KnowledgeFragment
from hub_platform.ai.provider.base import ProviderError


def _release_fragments(release: ChannelAIRelease):
    version_ids = release.knowledge_versions.values_list("knowledge_version_id", flat=True)
    return KnowledgeFragment.objects.filter(version_id__in=version_ids).select_related("version__document")


def lexical_search(release: ChannelAIRelease, query: str, *, limit: int = 5) -> list[KnowledgeFragment]:
    if not query.strip():
        return []
    search_query = SearchQuery(query, search_type="websearch")
    return list(
        _release_fragments(release)
        .annotate(rank=SearchRank(SearchVector("content"), search_query))
        .filter(rank__gt=0)
        .order_by("-rank")[:limit]
    )


def semantic_search(release: ChannelAIRelease, query_vector: list[float], *, limit: int = 5) -> list[KnowledgeFragment]:
    return list(
        _release_fragments(release)
        .filter(embedding__isnull=False)
        .order_by(CosineDistance("embedding", query_vector))[:limit]
    )


class KnowledgeRetriever:
    """Hybrid retriever: semantic (pgvector) primary, lexical (Postgres FTS) complementary."""

    def retrieve(self, *, release: ChannelAIRelease, query: str, limit: int = 5) -> list[KnowledgeFragment]:
        # Семантический поиск опционален: если провайдер не даёт эмбеддинги —
        # работаем на лексическом (Postgres FTS), не падая.
        try:
            query_vector = embed_texts(
                channel=release.channel,
                texts=[query],
                model=settings.HUB_AI_EMBEDDING_MODEL,
                purpose="retrieval_query",
            )[0].vector
            semantic = semantic_search(release, query_vector, limit=limit)
        except ProviderError:
            semantic = []
        lexical = lexical_search(release, query, limit=limit)
        seen = {fragment.id for fragment in semantic}
        merged = semantic + [fragment for fragment in lexical if fragment.id not in seen]
        return merged[:limit]
