from hub_platform.ai.models import (
    AIAgent,
    Knowledge,
    KnowledgeAttachment,
    KnowledgeCategory,
)
from hub_platform.identity.models import Department


def _channel_ref(channel) -> dict[str, object]:
    return {
        "id": channel.id,
        "code": channel.code,
        "name": channel.name,
        "product": {"code": channel.product.code, "name": channel.product.name} if channel.product_id else None,
        "providerIntegrationId": channel.provider_integration_id,
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


def department_ref_payload(department: Department) -> dict[str, object]:
    return {
        "id": department.id,
        "code": department.code,
        "name": department.name,
    }


def knowledge_payload(knowledge: Knowledge, *, include_content: bool = True) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": knowledge.id,
        "title": knowledge.title,
        "description": knowledge.description,
        "category": category_ref_payload(knowledge.category),
        "visibility": knowledge.visibility,
        "departments": [
            department_ref_payload(department)
            for department in knowledge.departments.all()
        ],
        "isEnabled": knowledge.is_enabled,
        "attachments": [attachment_payload(attachment) for attachment in knowledge.attachments.all()],
        "agentsCount": getattr(knowledge, "agents_count", None),
        "createdAt": knowledge.created_at.isoformat(),
        "updatedAt": knowledge.updated_at.isoformat(),
    }
    if include_content:
        payload["content"] = knowledge.content
    return payload


def agent_payload(agent: AIAgent) -> dict[str, object]:
    return {
        "id": agent.id,
        "channel": _channel_ref(agent.channel),
        "name": agent.name,
        "isActive": agent.is_active,
        "status": agent.status,
        "model": agent.model,
        "credentialMode": agent.credential_mode,
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
        "createdAt": agent.created_at.isoformat(),
        "updatedAt": agent.updated_at.isoformat(),
    }
