from django.conf import settings

from hub_platform.ai.chunking import chunk_text
from hub_platform.ai.invocation import embed_texts
from hub_platform.ai.models import KnowledgeDocumentVersion, KnowledgeFragment
from hub_platform.ai.provider.base import ProviderError


def reindex_knowledge_version(version: KnowledgeDocumentVersion) -> list[KnowledgeFragment]:
    """Rebuild fragments (+ embeddings if available) for a published knowledge
    version (ADR-HUB-0016). If the provider has no embeddings, fragments are
    still stored for lexical (Postgres FTS) search."""
    KnowledgeFragment.objects.filter(version=version).delete()
    chunks = chunk_text(version.content)
    if not chunks:
        return []
    try:
        embeddings = embed_texts(channel=None, texts=chunks, model=settings.HUB_AI_EMBEDDING_MODEL, purpose="knowledge_index")
        vectors = [result.vector for result in embeddings]
    except ProviderError:
        vectors = [None] * len(chunks)
    fragments = [
        KnowledgeFragment(version=version, chunk_index=index, content=chunk, embedding=vector)
        for index, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    return KnowledgeFragment.objects.bulk_create(fragments)
