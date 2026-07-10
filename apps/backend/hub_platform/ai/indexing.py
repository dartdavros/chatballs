from django.conf import settings

from hub_platform.ai.chunking import chunk_text
from hub_platform.ai.invocation import embed_texts
from hub_platform.ai.models import Knowledge, KnowledgeAttachment, KnowledgeFragment
from hub_platform.ai.provider.base import ProviderError


def reindex_knowledge(knowledge: Knowledge) -> list[KnowledgeFragment]:
    """Rebuild fragments (+ embeddings if available) for a knowledge item
    (ADR-HUB-0016/0023): content plus extracted text of its attachments.
    If the provider has no embeddings, fragments are still stored for
    lexical (Postgres FTS) search."""
    KnowledgeFragment.objects.filter(knowledge=knowledge).delete()
    sources = [knowledge.content]
    # Явный запрос вместо knowledge.attachments.all(): related manager может
    # держать устаревший prefetch-кэш (например, только что удалённое вложение).
    for attachment in KnowledgeAttachment.objects.filter(knowledge=knowledge).exclude(extracted_text=""):
        sources.append(f"Файл {attachment.original_name}:\n{attachment.extracted_text}")
    chunks = [chunk for source in sources for chunk in chunk_text(source)]
    if not chunks:
        return []
    try:
        embeddings = embed_texts(channel=None, texts=chunks, model=settings.HUB_AI_EMBEDDING_MODEL, purpose="knowledge_index")
        vectors = [result.vector for result in embeddings]
    except ProviderError:
        vectors = [None] * len(chunks)
    fragments = [
        KnowledgeFragment(knowledge=knowledge, chunk_index=index, content=chunk, embedding=vector)
        for index, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    return KnowledgeFragment.objects.bulk_create(fragments)
