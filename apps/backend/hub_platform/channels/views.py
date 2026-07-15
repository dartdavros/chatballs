from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai.provider.base import ProviderError
from hub_platform.api.permissions import HasCapability
from hub_platform.channels.models import Channel
from hub_platform.channels.runtime import run_channel_turn
from hub_platform.channels.selectors import channel_for_context, channels_for_context
from hub_platform.channels.serializers import channel_payload
from hub_platform.channels.services import ChannelInput, update_channel
from hub_platform.identity.audit import record_audit_event


class ChannelListView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.view"
    require_organization_scope = True

    def get(self, request: Request) -> Response:
        items = channels_for_context(request.tenant_context)
        return Response({"items": [channel_payload(channel) for channel in items]})


class ChannelDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"
    require_organization_scope = True

    def patch(self, request: Request, channel_id: int) -> Response:
        try:
            channel = channel_for_context(
                context=request.tenant_context, channel_id=channel_id
            )
        except Channel.DoesNotExist:
            return Response({"detail": "Канал не найден"}, status=404)
        name = str(request.data.get("name", channel.name)).strip()
        if not name:
            return Response({"detail": "Название канала не может быть пустым"}, status=400)
        channel = update_channel(
            context=request.tenant_context,
            channel=channel,
            data=ChannelInput(name=name),
        )
        record_audit_event(
            action="channels.channel_renamed",
            actor=request.user,
            organization=request.tenant_context.organization,
            object_type="Channel",
            object_id=str(channel.id),
            request=request,
        )
        return Response({"channel": channel_payload(channel)})


class ChannelTestChatView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"
    require_organization_scope = True

    def post(self, request: Request, channel_id: int) -> Response:
        try:
            channel = channel_for_context(
                context=request.tenant_context, channel_id=channel_id
            )
        except Channel.DoesNotExist:
            return Response({"detail": "Канал не найден"}, status=404)
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
