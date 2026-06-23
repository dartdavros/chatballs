from hub_platform.ai.models import AIAgent, KnowledgeDocument, PromptDocument


def _version_payload(version) -> dict[str, object]:
    return {
        "id": version.id,
        "version": version.version,
        "status": version.status,
        "content": version.content,
        "createdBy": version.created_by_id,
        "createdAt": version.created_at.isoformat(),
    }


def _document_payload(document, extra: dict[str, object]) -> dict[str, object]:
    return {
        "id": document.id,
        "product": {"code": document.product.code, "name": document.product.name},
        "code": document.code,
        "title": document.title,
        "category": document.category,
        "isEnabled": document.is_enabled,
        "versions": [_version_payload(version) for version in document.versions.all()],
        "createdAt": document.created_at.isoformat(),
        "updatedAt": document.updated_at.isoformat(),
        **extra,
    }


def knowledge_payload(document: KnowledgeDocument) -> dict[str, object]:
    return _document_payload(document, {"inclusionMode": document.inclusion_mode})


def prompt_payload(document: PromptDocument) -> dict[str, object]:
    return _document_payload(document, {})


def agent_payload(agent: AIAgent) -> dict[str, object]:
    return {
        "id": agent.id,
        "product": {"code": agent.product.code, "name": agent.product.name},
        "name": agent.name,
        "isActive": agent.is_active,
        "model": agent.model,
        "modelParams": agent.model_params,
        "allowedTools": agent.allowed_tools,
        "limits": agent.limits,
        "createdAt": agent.created_at.isoformat(),
        "updatedAt": agent.updated_at.isoformat(),
    }
