"""HTTP-слой карточек агентов (/api/v1/agents/, ADR-CHATBALLS-0041 §4)."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ai.agent_card import (
    agent_card_for_context,
    agent_card_payload,
    agent_cards_for_context,
    create_agent_card,
    delete_agent_card,
    set_agent_card_active,
    update_agent_card,
)
from chatballs.ai.provider.base import ProviderError
from chatballs.api.pagination import page_payload, paginate
from chatballs.api.permissions import HasCapability
from chatballs.channels import services as channel_services
from chatballs.channels.models import Channel
from chatballs.channels.runtime import run_channel_turn
from chatballs.channels.selectors import channel_for_context
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event


# Функция, а не константа: язык у каждого запроса свой, а константа собралась бы
# один раз при импорте — на языке, который случайно стоял в тот момент.
def agent_not_found() -> dict[str, str]:
    return {"detail": t("ai.agent_not_found")}


def _validation_detail(error: ValidationError) -> str:
    if hasattr(error, "message_dict"):
        return "; ".join(
            message
            for messages in error.message_dict.values()
            for message in messages
        )
    return "; ".join(error.messages)


def _load(request: Request, agent_id: int) -> Channel:
    return agent_card_for_context(
        context=request.tenant_context, agent_id=agent_id
    )


def _audit(request: Request, action: str, channel: Channel, **payload: object) -> None:
    record_audit_event(
        action=action,
        actor=request.user,
        organization=request.tenant_context.organization,
        object_type="Agent",
        object_id=str(channel.id),
        payload=payload or None,
        request=request,
    )


# Справочник агентов для выпадающих выборов: фильтр библиотеки знаний, привязка
# материалов к агенту. Только идентификаторы и имя — карточки целиком этим
# экранам не нужны. Потолок защищает выбор от организации на тысячу агентов:
# при его достижении выбору нужен серверный поиск, а не молчаливая обрезка.
AGENT_DIRECTORY_LIMIT = 200


class AgentDirectoryView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "ai.view"}

    def get(self, request: Request) -> Response:
        cards = agent_cards_for_context(request.tenant_context).annotate(
            knowledge_count=Count("ai_agent__knowledge_items", distinct=True)
        )
        query = request.query_params.get("q", "").strip()
        if query:
            cards = cards.filter(Q(name__icontains=query) | Q(code__icontains=query))
        items = [
            {
                "id": channel.id,
                "aiAgentId": channel.ai_agent.id if hasattr(channel, "ai_agent") else None,
                "name": channel.name,
                "groupName": channel.group.name if channel.group_id else None,
                "aiStatus": channel.ai_agent.status if hasattr(channel, "ai_agent") else None,
                "isActive": channel.is_active,
                "knowledgeCount": channel.knowledge_count,
            }
            for channel in cards.order_by("name")[: AGENT_DIRECTORY_LIMIT + 1]
        ]
        return Response(
            {"items": items[:AGENT_DIRECTORY_LIMIT], "hasMore": len(items) > AGENT_DIRECTORY_LIMIT}
        )


class AgentCardListView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "ai.view", "POST": "ai.manage"}

    def get(self, request: Request) -> Response:
        cards = agent_cards_for_context(request.tenant_context)
        group = request.query_params.get("group")
        if group == "none":
            cards = cards.filter(group__isnull=True)
        elif group:
            try:
                cards = cards.filter(group_id=int(group))
            except ValueError:
                return Response({"detail": t("ai.group_id_or_none")}, status=400)
        from chatballs.ai.agent_card import (
            ensure_channel_agent,
            knowledge_total_for_organization,
        )

        query = request.query_params.get("q", "").strip()
        if query:
            cards = cards.filter(Q(name__icontains=query) | Q(code__icontains=query))
        total = knowledge_total_for_organization(request.tenant_context.organization_id)
        page = paginate(cards, request.query_params)

        def payload(channel):
            # Страховка для каналов, созданных в обход мастера.
            ensure_channel_agent(channel)
            return agent_card_payload(channel, knowledge_total=total)

        return Response(page_payload(page, payload))

    def post(self, request: Request) -> Response:
        data = request.data if isinstance(request.data, dict) else {}
        group_id = data.get("groupId")
        if group_id is not None and (
            isinstance(group_id, bool) or not isinstance(group_id, int)
        ):
            return Response({"detail": t("ai.group_id_integer_or_null")}, status=400)
        try:
            channel = create_agent_card(
                context=request.tenant_context,
                name=data.get("name"),
                group_id=group_id,
            )
        except ValidationError as error:
            return Response({"detail": _validation_detail(error)}, status=400)
        _audit(request, "ai.agent_created", channel, name=channel.name)
        return Response(
            {"agent": agent_card_payload(_load(request, channel.id))}, status=201
        )


class AgentCardDetailView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {
        "GET": "ai.view",
        "PATCH": "ai.manage",
        "DELETE": "ai.manage",
    }

    def get(self, request: Request, agent_id: int) -> Response:
        try:
            channel = _load(request, agent_id)
        except Channel.DoesNotExist:
            return Response(agent_not_found(), status=404)
        from chatballs.ai.agent_card import ensure_channel_agent

        ensure_channel_agent(channel)
        return Response({"agent": agent_card_payload(channel)})

    def patch(self, request: Request, agent_id: int) -> Response:
        try:
            channel = _load(request, agent_id)
        except Channel.DoesNotExist:
            return Response(agent_not_found(), status=404)
        body = request.data if isinstance(request.data, dict) else {}
        try:
            channel = update_agent_card(
                context=request.tenant_context, channel=channel, body=body
            )
        except ValidationError as error:
            return Response({"detail": _validation_detail(error)}, status=400)
        _audit(request, "ai.agent_updated", channel, fields=sorted(body.keys()))
        return Response({"agent": agent_card_payload(channel)})

    def delete(self, request: Request, agent_id: int) -> Response:
        try:
            channel = _load(request, agent_id)
        except Channel.DoesNotExist:
            return Response(agent_not_found(), status=404)
        name = channel.name
        try:
            delete_agent_card(context=request.tenant_context, channel=channel)
        except channel_services.ChannelHasReferences as error:
            return Response(error.payload(), status=409)
        _audit(request, "ai.agent_deleted", channel, name=name)
        return Response(status=204)


class _AgentCardStatusView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"
    target_active: bool

    def post(self, request: Request, agent_id: int) -> Response:
        try:
            channel = _load(request, agent_id)
        except Channel.DoesNotExist:
            return Response(agent_not_found(), status=404)
        try:
            channel = set_agent_card_active(
                context=request.tenant_context,
                channel=channel,
                is_active=self.target_active,
            )
        except ValidationError as error:
            return Response({"detail": _validation_detail(error)}, status=400)
        return Response({"agent": agent_card_payload(channel)})


class AgentCardActivateView(_AgentCardStatusView):
    target_active = True


class AgentCardDeactivateView(_AgentCardStatusView):
    target_active = False


class AgentCardTestChatView(APIView):
    permission_classes = [HasCapability]
    # Исполняет агента, а не изменяет канал: остаётся на ai.manage (ADR-HUB-0037 §9).
    required_capability = "ai.manage"

    def post(self, request: Request, agent_id: int) -> Response:
        try:
            channel = channel_for_context(
                context=request.tenant_context,
                channel_id=agent_id,
                capability="ai.view",
            )
        except Channel.DoesNotExist:
            return Response(agent_not_found(), status=404)
        message = str(request.data.get("message", "")).strip()
        if not message:
            return Response({"detail": t("ai.empty_message")}, status=400)
        history = request.data.get("history") or []
        if not isinstance(history, list):
            return Response({"detail": t("ai.history_must_be_list")}, status=400)
        try:
            result = run_channel_turn(channel=channel, message=message, history=history)
        except ProviderError as error:
            return Response({"detail": t("ai.provider_error", error=error)}, status=502)
        return Response(
            {
                "reply": result.text,
                "model": result.model,
                "promptTokens": result.prompt_tokens,
                "completionTokens": result.completion_tokens,
            }
        )


class AgentCardConnectionsView(APIView):
    permission_classes = [HasCapability]
    required_capability = "integrations.manage"

    def post(self, request: Request, agent_id: int) -> Response:
        try:
            channel = _load(request, agent_id)
        except Channel.DoesNotExist:
            return Response(agent_not_found(), status=404)
        data = request.data if isinstance(request.data, dict) else {}
        integration_id = data.get("integrationId")
        if isinstance(integration_id, bool) or not isinstance(integration_id, int):
            return Response({"detail": t("ai.integration_id_integer")}, status=400)
        try:
            integration, previous_channel_id = channel_services.bind_connection(
                context=request.tenant_context,
                channel=channel,
                integration_id=integration_id,
                force=bool(data.get("force")),
            )
        except channel_services.ConnectionAlreadyBound as error:
            return Response(error.payload(), status=409)
        except ValidationError as error:
            return Response({"detail": _validation_detail(error)}, status=400)
        if previous_channel_id is not None:
            _audit(
                request,
                "channels.connection_moved",
                channel,
                integrationId=integration.id,
                fromChannelId=previous_channel_id,
            )
        else:
            _audit(
                request,
                "channels.connection_bound",
                channel,
                integrationId=integration.id,
            )
        return Response({"agent": agent_card_payload(_load(request, channel.id))})


class AgentCardConnectionDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "integrations.manage"

    def delete(self, request: Request, agent_id: int, integration_id: int) -> Response:
        try:
            channel = _load(request, agent_id)
        except Channel.DoesNotExist:
            return Response(agent_not_found(), status=404)
        try:
            channel_services.unbind_connection(
                context=request.tenant_context,
                channel=channel,
                integration_id=integration_id,
            )
        except ValidationError as error:
            return Response({"detail": _validation_detail(error)}, status=400)
        _audit(
            request,
            "channels.connection_unbound",
            channel,
            integrationId=integration_id,
        )
        return Response({"agent": agent_card_payload(_load(request, channel.id))})
