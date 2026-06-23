from hub_platform.ai.models import AIAgent, KnowledgeDocument, ProductAIRelease, PromptDocument


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


def release_payload(release: ProductAIRelease) -> dict[str, object]:
    return {
        "id": release.id,
        "product": {"code": release.product.code, "name": release.product.name},
        "version": release.version,
        "status": release.status,
        "model": release.model,
        "modelParams": release.model_params,
        "allowedTools": release.allowed_tools,
        "limits": release.limits,
        "retrievalIndexVersion": release.retrieval_index_version,
        "notes": release.notes,
        "knowledgeVersions": [
            {"document": link.knowledge_version.document.code, "version": link.knowledge_version.version}
            for link in release.knowledge_versions.all()
        ],
        "promptVersions": [
            {"document": link.prompt_version.document.code, "version": link.prompt_version.version}
            for link in release.prompt_versions.all()
        ],
        "createdAt": release.created_at.isoformat(),
        "publishedAt": release.published_at.isoformat() if release.published_at else None,
    }


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
