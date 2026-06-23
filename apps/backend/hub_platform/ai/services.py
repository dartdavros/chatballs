from dataclasses import dataclass

from hub_platform.ai.models import AIAgent


@dataclass(frozen=True)
class AgentInput:
    name: str
    model: str
    model_params: dict
    allowed_tools: list
    limits: dict


def update_agent(*, agent: AIAgent, data: AgentInput) -> AIAgent:
    agent.name = data.name
    agent.model = data.model
    agent.model_params = data.model_params
    agent.allowed_tools = data.allowed_tools
    agent.limits = data.limits
    agent.save(update_fields=["name", "model", "model_params", "allowed_tools", "limits", "updated_at"])
    return agent


def set_agent_active(*, agent: AIAgent, is_active: bool) -> AIAgent:
    agent.is_active = is_active
    agent.save(update_fields=["is_active", "updated_at"])
    return agent
