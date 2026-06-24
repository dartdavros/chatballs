from django.conf import settings

from hub_platform.ai.chunking import chunk_text
from hub_platform.ai.invocation import embed_texts
from hub_platform.ai.models import KnowledgeDocumentVersion, KnowledgeFragment


def reindex_knowledge_version(version: KnowledgeDocumentVersion) -> list[KnowledgeFragment]:
    """Rebuild fragments + embeddings for a published knowledge version (ADR-HUB-0016)."""
    KnowledgeFragment.objects.filter(version=version).delete()
    chunks = chunk_text(version.content)
    if not chunks:
        return []
    embeddings = embed_texts(
        product=version.document.product,
        texts=chunks,
        model=settings.HUB_AI_EMBEDDING_MODEL,
        purpose="knowledge_index",
    )
    fragments = [
        KnowledgeFragment(version=version, chunk_index=index, content=chunk, embedding=result.vector)
        for index, (chunk, result) in enumerate(zip(chunks, embeddings))
    ]
    return KnowledgeFragment.objects.bulk_create(fragments)
