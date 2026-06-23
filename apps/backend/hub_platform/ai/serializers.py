from hub_platform.ai.models import AIAgent


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
