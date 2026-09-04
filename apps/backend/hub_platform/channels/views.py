from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai.models import AIAgentStatus
from hub_platform.ai.provider.base import ProviderError
from hub_platform.api.permissions import HasCapability
from hub_platform.channels import api_inputs, services
from hub_platform.channels.models import Channel
from hub_platform.channels.policy import PolicyInvariantError
from hub_platform.channels.runtime import run_channel_turn
from hub_platform.channels.selectors import (
    channel_for_context,
    channels_for_context,
    filter_channels,
)
from hub_platform.channels.serializers import channel_payload
from hub_platform.conversations.models import Conversation, LifecycleState
from hub_platform.identity.audit import record_audit_event
from hub_platform.integrations.models import IntegrationStatus

CHANNEL_NOT_FOUND = {"detail": "Канал не найден"}
PERIODS = {"today": None, "7d": 7, "30d": 30}


def _validation_detail(error: ValidationError) -> str:
    if hasattr(error, "message_dict"):
        return "; ".join(
            message for messages in error.message_dict.values() for message in messages
        )
    return "; ".join(error.messages)


def _audit(request: Request, action: str, channel: Channel, **payload) -> None:
    record_audit_event(
        action=action,
        actor=request.user,
        organization=request.tenant_context.organization,
        object_type="Channel",
        object_id=str(channel.id),
        payload=payload or {},
        request=request,
    )


def _load(request: Request, channel_id: int) -> Channel:
    return channel_for_context(context=request.tenant_context, channel_id=channel_id)


class ChannelListView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "channels.view", "POST": "channels.manage"}

    def get(self, request: Request) -> Response:
        items = filter_channels(
            channels_for_context(request.tenant_context), request.query_params
        )
        return Response({"items": [channel_payload(channel) for channel in items]})

    def post(self, request: Request) -> Response:
        data = request.data if isinstance(request.data, dict) else {}
        try:
            policy = api_inputs.parse_create_policy(data)
            connection_ids = api_inputs.parse_connection_ids(data.get("connectionIds"))
            channel = services.create_channel(
                context=request.tenant_context,
                code=data.get("code"),
                name=data.get("name"),
                group_id=data.get("groupId"),
                product_id=data.get("productId"),
                policy=policy,
                connection_ids=connection_ids,
            )
        except services.ChannelCodeConflict as error:
            return Response({"detail": str(error)}, status=409)
        except services.ConnectionAlreadyBound as error:
            return Response(error.payload(), status=409)
        except PolicyInvariantError as error:
            return Response(error.payload(), status=400)
        except ValidationError as error:
            return Response({"detail": _validation_detail(error)}, status=400)
        _audit(request, "channels.channel_created", channel, code=channel.code)
        return Response({"channel": channel_payload(_load(request, channel.id))}, status=201)


class ChannelDetailView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {
        "GET": "channels.view",
        "PATCH": "channels.manage",
        "DELETE": "channels.manage",
    }

    def get(self, request: Request, channel_id: int) -> Response:
        try:
            channel = _load(request, channel_id)
        except Channel.DoesNotExist:
            return Response(CHANNEL_NOT_FOUND, status=404)
        return Response({"channel": channel_payload(channel)})

    def patch(self, request: Request, channel_id: int) -> Response:
        try:
            channel = _load(request, channel_id)
        except Channel.DoesNotExist:
            return Response(CHANNEL_NOT_FOUND, status=404)
        data = request.data if isinstance(request.data, dict) else {}
        before = channel_payload(channel)
        try:
            update = api_inputs.parse_update(data, current_code=channel.code)
            channel = services.update_channel(
                context=request.tenant_context, channel=channel, update=update
            )
        except services.ChannelHasReferences as error:
            return Response(error.payload(), status=409)
        except PolicyInvariantError as error:
            return Response(error.payload(), status=400)
        except ValidationError as error:
            return Response({"detail": _validation_detail(error)}, status=400)

        channel = _load(request, channel.id)
        after = channel_payload(channel)
        diff = {
            key: {"from": before[key], "to": after[key]}
            for key in ("name", "groupId", "product", "isActive", "policy")
            if before[key] != after[key]
        }
        if diff:
            _audit(request, "channels.channel_updated", channel, diff=diff)
        if "isActive" in diff:
            _audit(
                request,
                "channels.channel_activation_changed",
                channel,
                isActive=after["isActive"],
            )

        body: dict[str, object] = {"channel": after}
        agent = after["agent"]
        # §7.4: деактивация не останавливает агента — он продолжает занимать слот.
        if diff.get("isActive", {}).get("to") is False and agent:
            if agent["status"] == AIAgentStatus.ACTIVE:
                body["warnings"] = [
                    {"code": "agent_still_active", "agentId": agent["id"]}
                ]
        return Response(body)

    def delete(self, request: Request, channel_id: int) -> Response:
        try:
            channel = _load(request, channel_id)
        except Channel.DoesNotExist:
            return Response(CHANNEL_NOT_FOUND, status=404)
        code = channel.code
        try:
            services.delete_channel(context=request.tenant_context, channel=channel)
        except services.ChannelHasReferences as error:
            return Response(error.payload(), status=409)
        record_audit_event(
            action="channels.channel_deleted",
            actor=request.user,
            organization=request.tenant_context.organization,
            object_type="Channel",
            object_id=str(channel_id),
            payload={"code": code},
            request=request,
        )
        return Response(status=204)


class ChannelConnectionsView(APIView):
    permission_classes = [HasCapability]
    required_capability = "integrations.manage"
    require_organization_scope = True

    def post(self, request: Request, channel_id: int) -> Response:
        try:
            channel = _load(request, channel_id)
        except Channel.DoesNotExist:
            return Response(CHANNEL_NOT_FOUND, status=404)
        data = request.data if isinstance(request.data, dict) else {}
        integration_id = data.get("integrationId")
        if isinstance(integration_id, bool) or not isinstance(integration_id, int):
            return Response({"detail": "integrationId must be an integer"}, status=400)
        try:
            integration, previous_channel_id = services.bind_connection(
                context=request.tenant_context,
                channel=channel,
                integration_id=integration_id,
                force=bool(data.get("force")),
            )
        except services.ConnectionAlreadyBound as error:
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
        return Response({"channel": channel_payload(_load(request, channel.id))})


class ChannelConnectionDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "integrations.manage"
    require_organization_scope = True

    def delete(self, request: Request, channel_id: int, integration_id: int) -> Response:
        try:
            channel = _load(request, channel_id)
        except Channel.DoesNotExist:
            return Response(CHANNEL_NOT_FOUND, status=404)
        try:
            services.unbind_connection(
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
        return Response({"channel": channel_payload(_load(request, channel.id))})


class ChannelCountersView(APIView):
    permission_classes = [HasCapability]
    required_capability = "channels.view"

    def get(self, request: Request, channel_id: int) -> Response:
        try:
            channel = _load(request, channel_id)
        except Channel.DoesNotExist:
            return Response(CHANNEL_NOT_FOUND, status=404)
        period = request.query_params.get("period", "7d")
        if period not in PERIODS:
            return Response({"detail": "period must be today, 7d or 30d"}, status=400)
        now = timezone.now()
        since = (
            now.replace(hour=0, minute=0, second=0, microsecond=0)
            if period == "today"
            else now - timedelta(days=PERIODS[period])
        )
        conversations = Conversation.objects.filter(channel=channel)
        connections = channel.connections.aggregate(
            total=Count("id"),
            ok=Count("id", filter=Q(status=IntegrationStatus.OK)),
            error=Count("id", filter=Q(status=IntegrationStatus.ERROR)),
        )
        return Response(
            {
                "period": period,
                "conversations": {
                    # Открытые считаются на сейчас, total — созданные за период.
                    "open": conversations.filter(lifecycle=LifecycleState.OPEN).count(),
                    "total": conversations.filter(created_at__gte=since).count(),
                },
                "connections": connections,
            }
        )


class ChannelTestChatView(APIView):
    permission_classes = [HasCapability]
    # Исполняет агента, а не изменяет канал: остаётся на ai.manage (ADR-HUB-0037 §9).
    required_capability = "ai.manage"
    require_organization_scope = True

    def post(self, request: Request, channel_id: int) -> Response:
        try:
            channel = channel_for_context(
                context=request.tenant_context,
                channel_id=channel_id,
                capability="ai.view",
            )
        except Channel.DoesNotExist:
            return Response(CHANNEL_NOT_FOUND, status=404)
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
