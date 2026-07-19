from hub_platform.channels.models import Channel
from hub_platform.channels.policy import ChannelPolicy


def _agent_payload(channel: Channel) -> dict[str, object] | None:
    """Сводка для ссылки на существующую страницу агента (SPEC-HUB-0027 §6.1).

    Конфигурация агента (persona, tone, instructions, allowedTools, limits,
    knowledgeIds) в payload канала не входит и через API канала не изменяется.
    Знаний и их счётчика здесь нет: знания принадлежат агенту.
    """
    agent = getattr(channel, "ai_agent", None)
    if agent is None:
        return None
    return {
        "id": agent.id,
        "name": agent.name,
        "status": agent.status,
        "model": agent.model,
    }


def _connections_payload(channel: Channel) -> list[dict[str, object]]:
    return [
        {
            "id": connection.id,
            "provider": connection.provider,
            "name": connection.name,
            "status": connection.status,
        }
        for connection in sorted(channel.connections.all(), key=lambda item: item.id)
    ]


def _open_conversations(channel: Channel) -> int:
    # Селекторы аннотируют счётчик одним агрегатом на список (SPEC §6.1):
    # запрос ниже — страховка для объектов, собранных в обход селектора.
    count = getattr(channel, "open_conversations_count", None)
    if count is None:
        from hub_platform.conversations.models import LifecycleState

        return channel.conversations.filter(lifecycle=LifecycleState.OPEN).count()
    return count


def channel_payload(channel: Channel) -> dict[str, object]:
    policy = ChannelPolicy.from_channel(channel)
    connections = _connections_payload(channel)
    agent = _agent_payload(channel)
    return {
        "id": channel.id,
        "code": channel.code,
        "name": channel.name,
        "isActive": channel.is_active,
        "product": {
            "id": channel.product.id,
            "code": channel.product.code,
            "name": channel.product.name,
        }
        if channel.product_id
        else None,
        "departmentId": channel.department_id,
        "department": channel.department.code if channel.department_id else None,
        "departmentName": channel.department.name if channel.department_id else None,
        "agent": agent,
        "connections": connections,
        "policy": policy.as_payload(),
        "counters": {
            "openConversations": _open_conversations(channel),
            "connections": len(connections),
        },
        "createdAt": channel.created_at.isoformat(),
        "updatedAt": channel.updated_at.isoformat(),
        # Read-only до переноса provider_integration на агента (SPEC §9).
        "providerIntegrationId": channel.provider_integration_id,
        # Совместимость на один релиз: плоские ключи политики и agentId живут
        # рядом с policy/agent и удаляются после перевода клиентов (SPEC §6.1).
        "agentId": agent["id"] if agent else None,
        **policy.as_payload(),
    }
