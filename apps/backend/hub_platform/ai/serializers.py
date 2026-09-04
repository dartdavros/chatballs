from hub_platform.ai.models import (
    AIAgent,
    Knowledge,
    KnowledgeAttachment,
    KnowledgeCategory,
)
from hub_platform.support_portals.addressing import article_public_url


def _channel_ref(channel) -> dict[str, object]:
    return {
        "id": channel.id,
        "code": channel.code,
        "name": channel.name,
        "product": {"code": channel.product.code, "name": channel.product.name} if channel.product_id else None,
        "group": (
            {"id": channel.group_id, "name": channel.group.name}
            if channel.group_id
            else None
        ),
    }


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


def agent_payload(agent: AIAgent) -> dict[str, object]:
    return {
        "id": agent.id,
        "channel": _channel_ref(agent.channel),
        "name": agent.name,
        "isActive": agent.is_active,
        "status": agent.status,
        "model": agent.model,
        "credentialMode": agent.credential_mode,
        # BYOK-провайдер принадлежит агенту (SPEC-HUB-0027 §9).
        "providerIntegrationId": agent.provider_integration_id,
        "modelParams": agent.model_params,
        "allowedTools": agent.allowed_tools,
        "limits": agent.limits,
        "persona": agent.persona,
        "tone": agent.tone,
        "instructions": agent.instructions,
        "knowledge": [
            {"id": knowledge.id, "title": knowledge.title, "isEnabled": knowledge.is_enabled}
            for knowledge in agent.knowledge_items.all()
        ],
        "portalArticles": [
            agent_portal_article_payload(article)
            for article in agent.portal_articles.all()
        ],
        "createdAt": agent.created_at.isoformat(),
        "updatedAt": agent.updated_at.isoformat(),
    }
