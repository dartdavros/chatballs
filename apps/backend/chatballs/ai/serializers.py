from chatballs.ai.models import (
    Knowledge,
    KnowledgeAttachment,
    KnowledgeCategory,
)
from chatballs.support_portals.addressing import article_public_url


def attachment_payload(attachment: KnowledgeAttachment) -> dict[str, object]:
    return {
        "id": attachment.id,
        "name": attachment.original_name,
        "contentType": attachment.content_type,
        "size": attachment.size,
        "hasText": bool(attachment.extracted_text),
        "url": attachment.public_url(),
        "createdAt": attachment.created_at.isoformat(),
    }


def category_ref_payload(category: KnowledgeCategory) -> dict[str, object]:
    return {
        "id": category.id,
        "name": category.name,
        "parentId": category.parent_id,
    }


def category_payload(category: KnowledgeCategory) -> dict[str, object]:
    return {
        **category_ref_payload(category),
        "sortOrder": category.sort_order,
        "isSystem": category.is_system,
        "knowledgeCount": getattr(category, "knowledge_count", None),
    }


def knowledge_payload(knowledge: Knowledge, *, include_content: bool = True) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": knowledge.id,
        "title": knowledge.title,
        "description": knowledge.description,
        "category": category_ref_payload(knowledge.category),
        "isEnabled": knowledge.is_enabled,
        "attachments": [attachment_payload(attachment) for attachment in knowledge.attachments.all()],
        "agentsCount": getattr(knowledge, "agents_count", None),
        "fragmentsCount": getattr(knowledge, "fragments_count", None),
        "createdAt": knowledge.created_at.isoformat(),
        "updatedAt": knowledge.updated_at.isoformat(),
    }
    if include_content:
        payload["content"] = knowledge.content
    return payload


def agent_portal_article_payload(article) -> dict[str, object]:
    """Статья портала в карточке агента: заголовок опубликованной ревизии и
    адреса — в Help Center и в разделе поддержки."""
    revision = article.published_revision
    return {
        "id": article.id,
        "title": revision.title if revision is not None else article.slug,
        "status": article.status,
        "portal": {"id": article.portal_id, "name": article.portal.name},
        "publicUrl": article_public_url(article),
    }
