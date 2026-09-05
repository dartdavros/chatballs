"""HTTP-слой карточек агентов (/api/v1/agents/, ADR-HUB-0041 §4)."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai.agent_card import (
    agent_card_for_context,
    agent_card_payload,
    agent_cards_for_context,
    create_agent_card,
    delete_agent_card,
    set_agent_card_active,
    update_agent_card,
)
from hub_platform.ai.provider.base import ProviderError
from hub_platform.api.permissions import HasCapability
from hub_platform.channels import services as channel_services
from hub_platform.channels.models import Channel
from hub_platform.channels.runtime import run_channel_turn
from hub_platform.channels.selectors import channel_for_context
from hub_platform.identity.audit import record_audit_event

AGENT_NOT_FOUND = {"detail": "Агент не найден"}


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
                return Response({"detail": "group must be an id or none"}, status=400)
        from hub_platform.ai.agent_card import ensure_channel_agent

        items = []
        for channel in cards:
            # Страховка для каналов, созданных в обход мастера.
            ensure_channel_agent(channel)
            items.append(agent_card_payload(channel))
        return Response({"items": items})

    def post(self, request: Request) -> Response:
        data = request.data if isinstance(request.data, dict) else {}
        group_id = data.get("groupId")
        if group_id is not None and (
            isinstance(group_id, bool) or not isinstance(group_id, int)
        ):
            return Response({"detail": "groupId must be an integer or null"}, status=400)
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
            return Response(AGENT_NOT_FOUND, status=404)
        from hub_platform.ai.agent_card import ensure_channel_agent

        ensure_channel_agent(channel)
        return Response({"agent": agent_card_payload(channel)})

    def patch(self, request: Request, agent_id: int) -> Response:
        try:
            channel = _load(request, agent_id)
        except Channel.DoesNotExist:
            return Response(AGENT_NOT_FOUND, status=404)
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
            return Response(AGENT_NOT_FOUND, status=404)
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
            return Response(AGENT_NOT_FOUND, status=404)
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
    require_organization_scope = True

    def post(self, request: Request, agent_id: int) -> Response:
        try:
            channel = channel_for_context(
                context=request.tenant_context,
                channel_id=agent_id,
                capability="ai.view",
            )
        except Channel.DoesNotExist:
            return Response(AGENT_NOT_FOUND, status=404)
        message = str(request.data.get("message", "")).strip()
        if not message:
            return Response({"detail": "Пустое сообщение"}, status=400)
        history = request.data.get("history") or []
        if not isinstance(history, list):
            return Response({"detail": "history must be a list"}, status=400)
        try:
            result = run_channel_turn(channel=channel, message=message, history=history)
        except ProviderError as error:
            return Response({"detail": f"Ошибка провайдера: {error}"}, status=502)
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
            return Response(AGENT_NOT_FOUND, status=404)
        data = request.data if isinstance(request.data, dict) else {}
        integration_id = data.get("integrationId")
        if isinstance(integration_id, bool) or not isinstance(integration_id, int):
            return Response({"detail": "integrationId must be an integer"}, status=400)
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
            return Response(AGENT_NOT_FOUND, status=404)
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
