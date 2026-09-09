from django.conf import settings

from chatballs.ai.chunking import chunk_text
from chatballs.ai.invocation import embed_texts
from chatballs.ai.models import Knowledge, KnowledgeAttachment, KnowledgeFragment
from chatballs.ai.provider.base import ProviderError


def _store_fragments(*, organization, chunks: list[str], **source) -> list[KnowledgeFragment]:
    """Сохранить чанки одного источника (+ эмбеддинги, если провайдер их даёт).
    Без эмбеддингов фрагменты всё равно пишутся: остаётся лексический поиск
    (Postgres FTS)."""
    if not chunks:
        return []
    try:
        embeddings = embed_texts(
            organization=organization,
            texts=chunks,
            model=settings.CHATBALLS_AI_EMBEDDING_MODEL,
            purpose="knowledge_index",
        )
        vectors = [result.vector for result in embeddings]
    except ProviderError:
        vectors = [None] * len(chunks)
    fragments = [
        KnowledgeFragment(
            organization=organization,
            chunk_index=index,
            content=chunk,
            embedding=vector,
            **source,
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=False))
    ]
    return KnowledgeFragment.objects.bulk_create(fragments)


def reindex_knowledge(knowledge: Knowledge) -> list[KnowledgeFragment]:
    """Rebuild fragments for a knowledge item (ADR-CHATBALLS-0016/0023): content plus
    extracted text of its attachments."""
    KnowledgeFragment.objects.filter(knowledge=knowledge).delete()
    sources = [knowledge.content]
    # Явный запрос вместо knowledge.attachments.all(): related manager может
    # держать устаревший prefetch-кэш (например, только что удалённое вложение).
    for attachment in KnowledgeAttachment.objects.filter(knowledge=knowledge).exclude(extracted_text=""):
        sources.append(f"Файл {attachment.original_name}:\n{attachment.extracted_text}")
    chunks = [chunk for source in sources for chunk in chunk_text(source)]
    return _store_fragments(
        organization=knowledge.organization,
        chunks=chunks,
        knowledge=knowledge,
    )


def reindex_portal_article(article) -> list[KnowledgeFragment]:
    """Rebuild fragments for a support portal article.

    Индексируется только опубликованная ревизия: агент отвечает тем же
    текстом, который клиент видит в Help Center. У черновика и архива
    фрагментов нет, поэтому в выдачу они не попадают.
    """
    from chatballs.support_portals.statuses import ArticleStatus

    KnowledgeFragment.objects.filter(portal_article=article).delete()
    revision = article.published_revision
    if article.status != ArticleStatus.PUBLISHED or revision is None:
        return []
    heading = revision.title
    if revision.summary.strip():
        heading = f"{heading}\n\n{revision.summary.strip()}"
    chunks = chunk_text(f"{heading}\n\n{revision.content}")
    return _store_fragments(
        organization=article.organization,
        chunks=chunks,
        portal_article=article,
    )
