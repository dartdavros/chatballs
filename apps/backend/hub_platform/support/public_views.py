from django.db import models
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

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
    web_widget_route,
)
from hub_platform.webchat.models import (
    WebChatWidget,
    WebChatWidgetMode,
    WebChatWidgetStatus,
)
from hub_platform.webchat.services import origin_allowed


class _Public(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]


class SupportSessionStartView(_Public):
    def post(self, request: Request) -> Response:
        widget_key = str(request.data.get("widgetKey", "")).strip()
        channel_code = str(request.data.get("channel", "")).strip()
        token = str(request.data.get("token", ""))
        if not token or (not widget_key and not channel_code):
            return _denied()
        if widget_key:
            route = web_widget_route(widget_key)
            if route is None:
                return _denied()
            channel_id = None
        else:
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
            channel_id = int(route.resource_id)
        try:
            organization = Organization.objects.get(pk=route.organization_id)
        except Organization.DoesNotExist:
            return _denied()
        context = TenantContext.for_resource(organization)
        with tenant_atomic(context):
            widgets = WebChatWidget.objects.select_related(
                "organization",
                "integration",
                "integration__channel",
                "integration__channel__department",
                "integration__channel__product",
            ).filter(
                organization=organization,
                mode=WebChatWidgetMode.AUTHENTICATED_PRODUCT,
                status=WebChatWidgetStatus.PUBLISHED,
                integration__provider="WEB",
                integration__status="OK",
                integration__is_active=True,
                integration__channel__is_active=True,
            )
            if widget_key:
                widget = widgets.filter(
                    id=route.resource_id,
                    public_key=widget_key,
                ).first()
            else:
                candidates = list(
                    widgets.filter(
                        integration__channel_id=channel_id,
                        integration__channel__code=channel_code,
                    ).order_by("id")[:2]
                )
                widget = candidates[0] if len(candidates) == 1 else None
            origin = str(
                request.data.get("hostOrigin", "")
                or request.headers.get("Origin")
                or request.headers.get("Referer")
                or ""
            )
            if widget is None or not origin_allowed(widget, origin):
                return _denied()
            try:
                result = start_support_session(
                    widget=widget,
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
