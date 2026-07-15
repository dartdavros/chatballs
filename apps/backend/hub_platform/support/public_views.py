from django.db import models
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.channels.models import Channel
from hub_platform.conversations.models import Conversation
from hub_platform.conversations.serializers import conversation_payload
from hub_platform.identity.models import Organization
from hub_platform.support import errors
from hub_platform.support.messages import post_support_message, support_messages_since
from hub_platform.support.serializers import support_identity_snapshot_payload
from hub_platform.support.session import start_support_session
from hub_platform.support.token import verify_support_token
from hub_platform.support.widget_credential import verify_widget_credential
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.database import tenant_atomic
from hub_platform.tenancy.ingress import (
    support_channel_routes,
    support_conversation_route,
)


class _Public(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]


class SupportSessionStartView(_Public):
    def post(self, request: Request) -> Response:
        channel_code = str(request.data.get("channel", "")).strip()
        token = str(request.data.get("token", ""))
        if not channel_code or not token:
            return _denied()
        routes = support_channel_routes(channel_code)
        if len(routes) == 1:
            route = routes[0]
        else:
            verified = []
            for candidate in routes:
                try:
                    verify_support_token(token=token, secret=candidate.support_secret)
                except errors.SupportSessionError:
                    continue
                verified.append(candidate)
            if len(verified) != 1:
                return _denied()
            route = verified[0]
        try:
            organization = Organization.objects.get(pk=route.organization_id)
        except Organization.DoesNotExist:
            return _denied()
        context = TenantContext.for_resource(organization)
        with tenant_atomic(context):
            channel = Channel.objects.select_related(
                "department", "product", "organization"
            ).filter(
                id=route.resource_id,
                organization=organization,
                code=channel_code,
                is_active=True,
            ).first()
            if channel is None:
                return _denied()
            try:
                result = start_support_session(
                    channel=channel,
                    token=token,
                    request=request,
                )
            except errors.SupportSessionError:
                return _denied()
        return Response(
            {
                "conversation": conversation_payload(
                    result["conversation"],
                    with_messages=True,
                ),
                "snapshot": support_identity_snapshot_payload(result["snapshot"]),
                "widgetCredential": result["widget_credential"],
            },
            status=201,
        )


def _widget_context(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    claims = verify_widget_credential(auth[7:])
    if claims is None:
        return None
    route = support_conversation_route(
        claims["conversation_id"],
        claims["snapshot_id"],
    )
    if route is None:
        return None
    try:
        organization = Organization.objects.get(pk=route.organization_id)
    except Organization.DoesNotExist:
        return None
    return TenantContext.for_resource(organization), claims


def _resolve_widget_conversation(
    context: TenantContext,
    claims,
) -> Conversation | None:
    return (
        Conversation.objects.select_related(
            "organization", "channel", "support_identity_snapshot"
        )
        .filter(
            id=claims["conversation_id"],
            support_identity_snapshot_id=claims["snapshot_id"],
            organization=context.organization,
            organization_id=models.F("support_identity_snapshot__organization_id"),
            channel__organization_id=models.F("organization_id"),
        )
        .first()
    )


class SupportSessionMessagesView(_Public):
    def get(self, request: Request) -> Response:
        resolved = _widget_context(request)
        if resolved is None:
            return Response({"detail": "Сессия не найдена"}, status=401)
        context, claims = resolved
        try:
            since = int(request.GET.get("since", "0") or 0)
        except ValueError:
            since = 0
        with tenant_atomic(context):
            conversation = _resolve_widget_conversation(context, claims)
            if conversation is None:
                return Response({"detail": "Сессия не найдена"}, status=401)
            return Response(support_messages_since(conversation, since))

    def post(self, request: Request) -> Response:
        resolved = _widget_context(request)
        if resolved is None:
            return Response({"detail": "Сессия не найдена"}, status=401)
        text = str(request.data.get("text", "")).strip()
        if not text:
            return Response({"detail": "Пустое сообщение"}, status=400)
        context, claims = resolved
        with tenant_atomic(context):
            conversation = _resolve_widget_conversation(context, claims)
            if conversation is None:
                return Response({"detail": "Сессия не найдена"}, status=401)
            post_support_message(
                context=context,
                conversation=conversation,
                text=text[:4000],
            )
            return Response({"ok": True}, status=201)


def _denied() -> Response:
    return Response(
        {
            "error": "support_unavailable",
            "message": errors.PUBLIC_SUPPORT_UNAVAILABLE,
        },
        status=422,
    )
