from hub_platform.ai.provider.base import ChatResult, ProviderError
from hub_platform.ai.runtime import run_agent_turn


def run_channel_turn(*, channel, message: str, history: list[dict] | None = None) -> ChatResult:
    """One AI turn for a processing channel (ADR-HUB-0019/0023).

    AI-поведение канала целиком определяет его агент. Без активного агента
    AI-ответа нет: вызывающий код (ingest/support) обрабатывает ProviderError
    как «AI недоступен» и передаёт диалог оператору.
    """
    agent = getattr(channel, "ai_agent", None)
    if agent is None or not agent.is_active:
        raise ProviderError("Channel has no active AI agent")
    return run_agent_turn(agent=agent, message=message, history=history, style_guard=True).result
