"""Агент как единая сущность (ADR-HUB-0041 §4, SPEC-HUB-0031 §4.3).

Для администратора существует только «Агент»: имя, группа, инструкции, знания,
подключения, активность. Физически карточка агрегирует Channel (несущая ось
диалогов/подключений) и AIAgent (конфигурация AI) 1:1; id карточки — id канала.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, QuerySet, Value, When
from django.utils.text import slugify

from chatballs.ai.models import AIAgent, AIAgentStatus
from chatballs.ai.provider_selection import configure_agent_provider
from chatballs.ai.serializers import agent_portal_article_payload
from chatballs.channels.models import Channel
from chatballs.channels.services import (
    CODE_MAX_LENGTH,
    UNSET,
    ChannelUpdate,
    update_channel,
)
from chatballs.conversations.models import LifecycleState
from chatballs.tenancy.context import TenantContext


def agent_cards_for_context(context: TenantContext) -> QuerySet[Channel]:
    return (
        Channel.objects.filter(organization_id=context.organization_id)
        .select_related("group", "ai_agent", "ai_agent__provider_integration")
        .prefetch_related(
            "connections__web_chat_widget",
            "ai_agent__knowledge_items",
            "ai_agent__portal_articles__portal",
            "ai_agent__portal_articles__published_revision",
        )
        .annotate(
            open_conversations_count=Count(
                "conversations",
                filter=Q(conversations__lifecycle=LifecycleState.OPEN),
                distinct=True,
            ),
            # Кадр G1: сверху отвечающие агенты, ниже «Без AI», выключенные — в конце.
            status_rank=Case(
                When(is_active=False, then=Value(2)),
                When(ai_agent__status=AIAgentStatus.ACTIVE, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        )
        .order_by("status_rank", "name")
    )


def agent_card_for_context(*, context: TenantContext, agent_id: int) -> Channel:
    return agent_cards_for_context(context).get(id=agent_id)


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
    Библиотека общая для организации (ADR-HUB-0041 §8), поэтому число одно
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


def agent_card_payload(channel: Channel, *, knowledge_total: int | None = None) -> dict[str, object]:
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
        "model": agent.model,
        "providerIntegrationId": agent.provider_integration_id,
        "modelParams": agent.model_params,
        "limits": agent.limits,
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
        "counters": {
            "openConversations": open_count,
            "connections": len(connections),
        },
        "createdAt": channel.created_at.isoformat(),
        "updatedAt": channel.updated_at.isoformat(),
    }


def _unique_agent_code(organization_id: int, name: str) -> str:
    base = slugify(name)[: CODE_MAX_LENGTH - 8].strip("-") or "agent"
    taken = set(
        Channel.objects.filter(
            organization_id=organization_id, code__startswith=base
        ).values_list("code", flat=True)
    )
    if base not in taken:
        return base
    for suffix in range(2, 1000):
        candidate = f"{base}-{suffix}"
        if candidate not in taken:
            return candidate
    raise ValidationError({"name": "Не удалось подобрать уникальный код агента"})


def ensure_channel_agent(channel: Channel) -> AIAgent:
    """AIAgent обязателен для каждого канала: DRAFT = AI не отвечает."""
    agent = getattr(channel, "ai_agent", None)
    if agent is not None:
        return agent
    agent = AIAgent.objects.create(
        channel=channel,
        name=channel.name,
        status=AIAgentStatus.DRAFT,
    )
    # Обновляем кеш select_related, чтобы payload не перечитывал канал.
    channel.ai_agent = agent
    return agent


@transaction.atomic
def create_agent_card(
    *, context: TenantContext, name: object, group_id: int | None
) -> Channel:
    """Мастер одного шага (SPEC-HUB-0031 §4.3): имя и необязательная группа.

    Канал создаётся без продукта с безопасной операторской политикой (дефолты
    модели удовлетворяют P1-P5); код генерируется из имени и неизменен.
    """
    from chatballs.channels import authorization
    from chatballs.channels.services import _clean_name, _group_for_channel

    authorization.require_organization_manage(context, operation="Создание агента")
    clean_name = _clean_name(name)
    group = _group_for_channel(context=context, group_id=group_id)
    channel = Channel.objects.create(
        organization_id=context.organization_id,
        code=_unique_agent_code(context.organization_id, clean_name),
        name=clean_name,
        group=group,
    )
    ensure_channel_agent(channel)
    return channel


@transaction.atomic
def update_agent_card(
    *, context: TenantContext, channel: Channel, body: dict[str, object]
) -> Channel:
    """PATCH одной карточки: канальные и AI-поля в одной транзакции."""
    agent = ensure_channel_agent(channel)

    update = ChannelUpdate(
        name=body["name"] if "name" in body else UNSET,
        group_id=body["groupId"] if "groupId" in body else UNSET,
        is_active=body["isActive"] if "isActive" in body else UNSET,
    )
    channel = update_channel(context=context, channel=channel, update=update)

    ai_fields = {
        "providerIntegrationId",
        "modelParams",
        "limits",
        "persona",
        "tone",
        "instructions",
        "knowledgeIds",
    }
    if ai_fields & set(body):
        from chatballs.ai.services import AgentInput, update_agent

        knowledge_ids = body.get("knowledgeIds")
        if knowledge_ids is not None and (
            not isinstance(knowledge_ids, list)
            or not all(isinstance(item, int) for item in knowledge_ids)
        ):
            raise ValidationError({"knowledgeIds": "List of ids required"})
        model_params = body.get("modelParams", agent.model_params)
        limits = body.get("limits", agent.limits)
        if not isinstance(model_params, dict):
            raise ValidationError({"modelParams": "Object required"})
        if not isinstance(limits, dict):
            raise ValidationError({"limits": "Object required"})
        provider_integration_id = body.get(
            "providerIntegrationId", agent.provider_integration_id
        )
        if provider_integration_id is not None and not isinstance(
            provider_integration_id, int
        ):
            raise ValidationError({"providerIntegrationId": "Integer id required"})
        update_agent(
            context=context,
            agent=agent,
            data=AgentInput(
                # Имя агента следует за именем карточки: сущность одна.
                name=channel.name,
                provider_integration_id=provider_integration_id,
                model_params=model_params,
                allowed_tools=agent.allowed_tools,
                limits=limits,
                persona=str(body.get("persona", agent.persona)),
                tone=str(body.get("tone", agent.tone)),
                instructions=str(body.get("instructions", agent.instructions)),
                knowledge_ids=knowledge_ids,
            ),
        )
    elif update.name is not UNSET:
        agent.name = channel.name
        agent.save(update_fields=["name", "updated_at"])
    return agent_card_for_context(context=context, agent_id=channel.id)


def agent_deletion_blockers(channel: Channel) -> list[dict[str, object]]:
    """Агент удаляется вместе с каналом; блокируют только внешние связи."""
    counts = (
        ("conversations", channel.conversations.count()),
        ("connections", channel.connections.count()),
        ("llmInvocations", channel.ai_invocations.count()),
    )
    return [{"type": name, "count": count} for name, count in counts if count]


@transaction.atomic
def delete_agent_card(*, context: TenantContext, channel: Channel) -> None:
    from chatballs.channels import authorization
    from chatballs.channels.services import ChannelHasReferences

    authorization.require_organization_manage(context, operation="Удаление агента")
    blockers = agent_deletion_blockers(channel)
    if blockers:
        raise ChannelHasReferences(blockers)
    AIAgent.objects.filter(channel=channel).delete()
    channel.delete()


def set_agent_card_active(
    *, context: TenantContext, channel: Channel, is_active: bool
) -> Channel:
    """Активность AI: включает/выключает автоответы, канал остаётся живым."""
    from chatballs.ai.services import set_agent_active

    agent = ensure_channel_agent(channel)
    set_agent_active(context=context, agent=agent, is_active=is_active)
    return agent_card_for_context(context=context, agent_id=channel.id)
