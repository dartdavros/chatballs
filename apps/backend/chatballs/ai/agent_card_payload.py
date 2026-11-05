"""Сериализация карточки агента и её подключений."""

from __future__ import annotations

from chatballs.ai.models import AIAgent
from chatballs.ai.serializers import agent_portal_article_payload
from chatballs.channels.models import Channel
from chatballs.conversations.models import LifecycleState


def _connection_payload(connection) -> dict[str, object]:
    """Подключение в карточке агента.

    Подпись строки собирается на фронте из этих полей: у Telegram — имя бота,
    у Web — домен сайта и публичный ключ виджета (из него собирается код
    вставки), у Email — адрес ящика.
    """
    config = connection.config or {}
    payload = {
        "id": connection.id,
        "provider": connection.provider,
        "name": connection.name,
        "status": connection.status,
        "botUsername": config.get("bot_username", ""),
        "email": config.get("email", ""),
        "allowedOrigins": config.get("allowed_domains", []),
        "widgetPublicKey": "",
    }
    if connection.provider == "WEB":
        from chatballs.webchat.widgets import widget_for_integration

        widget = widget_for_integration(connection)
        payload["widgetPublicKey"] = widget.public_key if widget is not None else ""
    return payload


def _connections_payload(channel: Channel) -> list[dict[str, object]]:
    return [
        _connection_payload(connection)
        for connection in sorted(channel.connections.all(), key=lambda item: item.id)
    ]


def knowledge_total_for_organization(organization_id: int) -> int:
    """Сколько всего материалов можно выбрать агенту — знаний библиотеки и
    опубликованных статей порталов («4 из 18» в шапке блока «Знания»).
    Библиотека общая для организации (ADR-CHATBALLS-0041 §8), поэтому число одно
    на всех агентов — список считает его один раз."""
    from chatballs.ai.models import Knowledge
    from chatballs.support_portals.models import PortalArticle
    from chatballs.support_portals.statuses import ArticleStatus

    return (
        Knowledge.objects.filter(organization_id=organization_id).count()
        + PortalArticle.objects.filter(
            organization_id=organization_id, status=ArticleStatus.PUBLISHED
        ).count()
    )


def _integration_model(integration, key: str) -> str:
    """Модель, заданная в интеграции: подсказка в поле модели на карточке."""
    if integration is None:
        return ""
    if key == "transcription_model":
        from chatballs.speech.contracts import capabilities

        return str(integration.config.get(key) or capabilities(integration.provider).default_model)
    return str((integration.config or {}).get(key) or "")


def agent_card_payload(
    channel: Channel,
    *,
    knowledge_total: int | None = None,
    check_tool_support: bool = False,
    with_tools: bool = True,
) -> dict[str, object]:
    """`check_tool_support` — спросить провайдера, если признака нет в кеше.

    Так делает только сама карточка: список агентов читает кеш и в сеть не ходит.
    Списку не нужны и инструменты (`with_tools`): их показывает карточка.
    """
    from chatballs.ai import tool_support
    from chatballs.ai.agent_tools import agent_tools_payload

    agent: AIAgent = channel.ai_agent
    connections = _connections_payload(channel)
    open_count = getattr(channel, "open_conversations_count", None)
    if open_count is None:
        open_count = channel.conversations.filter(lifecycle=LifecycleState.OPEN).count()
    return {
        "id": channel.id,
        "aiAgentId": agent.id,
        "code": channel.code,
        "name": channel.name,
        "isActive": channel.is_active,
        "groupId": channel.group_id,
        "groupName": channel.group.name if channel.group_id else None,
        # Цвет группы задаётся в настройках — точка у названия (кадры G1/G3).
        "groupColor": channel.group.color if channel.group_id else "",
        "aiStatus": agent.status,
        "assistanceEnabled": agent.assistance_enabled,
        # Модели агента: пустая строка означает «как в интеграции», и тогда
        # карточка показывает модель интеграции подсказкой в поле.
        "model": agent.model,
        "transcriptionModel": agent.transcription_model,
        "transcriptionLanguage": agent.transcription_language,
        "synthesisIntegrationId": agent.synthesis_integration_id,
        "synthesisModel": agent.synthesis_model,
        "synthesisVoice": agent.synthesis_voice,
        "providerModel": _integration_model(agent.provider_integration, "default_model"),
        "transcriptionProviderModel": _integration_model(
            agent.transcription_integration or agent.provider_integration,
            "transcription_model",
        ),
        # Вызывает ли модель ответов инструменты; null — пока неизвестно.
        "modelSupportsTools": (
            tool_support.resolve_tool_support(agent)
            if check_tool_support
            else tool_support.cached_tool_support(agent)
        ),
        "providerIntegrationId": agent.provider_integration_id,
        # Чем расшифровывать голосовые; пусто — тем же провайдером, что отвечает.
        "transcriptionIntegrationId": agent.transcription_integration_id,
        "modelParams": agent.model_params,
        "answerLanguage": agent.answer_language,
        "historyLimit": agent.history_limit,
        "persona": agent.persona,
        "tone": agent.tone,
        "instructions": agent.instructions,
        "knowledge": [
            {
                "id": item.id,
                "title": item.title,
                "isEnabled": item.is_enabled,
                "updatedAt": item.updated_at.isoformat(),
            }
            for item in agent.knowledge_items.all()
        ],
        "knowledgeTotal": knowledge_total
        if knowledge_total is not None
        else knowledge_total_for_organization(channel.organization_id),
        "portalArticles": [
            agent_portal_article_payload(article)
            for article in agent.portal_articles.all()
        ],
        "connections": connections,
        # Внешние серверы с инструментами: что доступно и что включено агенту.
        **({"tools": agent_tools_payload(agent)} if with_tools else {}),
        "counters": {
            "openConversations": open_count,
            "connections": len(connections),
        },
        "createdAt": channel.created_at.isoformat(),
        "updatedAt": channel.updated_at.isoformat(),
    }
