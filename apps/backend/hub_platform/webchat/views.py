from contextlib import contextmanager

from django.http import HttpResponse
from django.views import View
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.identity.models import Organization
from hub_platform.integrations.models import Integration, IntegrationProvider
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.database import tenant_atomic
from hub_platform.tenancy.ingress import web_channel_route, web_session_route
from hub_platform.webchat import services
from hub_platform.webchat.loader import LOADER_JS


def _origin(request: Request) -> str:
    return request.headers.get("Origin") or request.headers.get("Referer") or ""


def _token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    if request.method == "POST":
        return str(request.data.get("token", ""))
    return request.GET.get("token", "")


class _Public(APIView):
    authentication_classes: list = []  # публичные endpoint'ы: токен сессии, без CSRF/сессии Django
    permission_classes = [AllowAny]


@contextmanager
def _resolved_web_connection(channel_code: str):
    route = web_channel_route(channel_code)
    if route is None:
        yield None, None
        return
    try:
        organization = Organization.objects.get(pk=route.organization_id)
    except Organization.DoesNotExist:
        yield None, None
        return
    context = TenantContext.for_resource(organization)
    with tenant_atomic(context):
        integration = Integration.objects.select_related("channel").filter(
            id=route.resource_id,
            organization=organization,
            provider=IntegrationProvider.WEB,
            is_active=True,
            channel__organization=organization,
            channel__code=channel_code,
            channel__is_active=True,
        ).first()
        yield context, integration


@contextmanager
def _resolved_web_session(request: Request):
    token = _token(request)
    route = web_session_route(services.hash_session_token(token)) if token else None
    if route is None:
        yield None, None
        return
    try:
        organization = Organization.objects.get(pk=route.organization_id)
    except Organization.DoesNotExist:
        yield None, None
        return
    context = TenantContext.for_resource(organization)
    with tenant_atomic(context):
        session = services.resolve_session(
            context=context,
            token=token,
            session_id=int(route.resource_id),
        )
        yield context, session


class WebchatConfigView(_Public):
    def get(self, request: Request) -> Response:
        channel_code = request.GET.get("channel", "")
        with _resolved_web_connection(channel_code) as (context, integration):
            if context is None or integration is None:
                return Response({"available": False})
            if (
                integration.channel.requires_authenticated_product_identity
                or not integration.channel.allow_anonymous_sessions
            ):
                return Response({"available": False})
            return Response(
                services.public_config(
                    context=context,
                    integration=integration,
                    origin=_origin(request),
                )
            )


class WebchatSessionView(_Public):
    def post(self, request: Request) -> Response:
        channel_code = str(request.data.get("channel", ""))
        with _resolved_web_connection(channel_code) as (context, integration):
            if context is None or integration is None:
                return Response({"detail": "Канал недоступен"}, status=404)
            if (
                integration.channel.requires_authenticated_product_identity
                or not integration.channel.allow_anonymous_sessions
            ):
                return Response({"detail": "Канал недоступен"}, status=404)
            result = services.issue_session(context=context, integration=integration)
            if result is None:
                return Response({"detail": "Канал недоступен"}, status=404)
            return Response(result, status=201)


class WebchatMessagesView(_Public):
    def post(self, request: Request) -> Response:
        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": "Сессия не найдена"}, status=401)
            text = str(request.data.get("text", "")).strip()
            if not text:
                return Response({"detail": "Пустое сообщение"}, status=400)
            services.post_message(session, text[:4000])
            return Response({"ok": True}, status=201)

    def get(self, request: Request) -> Response:
        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": "Сессия не найдена"}, status=401)
            try:
                since = int(request.GET.get("since", "0") or 0)
            except ValueError:
                since = 0
            return Response(services.messages_payload(session, since))


class WebchatContactView(_Public):
    def post(self, request: Request) -> Response:
        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": "Сессия не найдена"}, status=401)
            phone = services.normalize_phone(str(request.data.get("phone", "")))
            if not phone:
                return Response({"detail": "Некорректный номер телефона"}, status=400)
            services.post_contact(session, phone)
            return Response({"ok": True}, status=201)


class WebchatCallOpenView(_Public):
    def post(self, request: Request) -> Response:
        from hub_platform.calls.errors import CallTokenError
        from hub_platform.calls.serializers import ice_servers_payload, public_invite_payload
        from hub_platform.calls.services import open_call_for_identity

        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": "Сессия не найдена"}, status=401)
            try:
                resolved = open_call_for_identity(identity=session.identity)
            except CallTokenError:
                return Response({"detail": "Активное приглашение не найдено"}, status=404)
            response = Response(
                {
                    "call": public_invite_payload(resolved.invite.call_session, resolved.invite.expires_at),
                    "accessToken": resolved.customer_access_token,
                    "iceServers": ice_servers_payload(),
                }
            )
            response["Cache-Control"] = "no-store"
            return response


class WebchatCallDeclineView(_Public):
    def post(self, request: Request) -> Response:
        from hub_platform.calls.errors import CallConflict, CallTokenError
        from hub_platform.calls.services import decline_call_for_identity

        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": "Сессия не найдена"}, status=401)
            try:
                decline_call_for_identity(identity=session.identity)
            except CallTokenError:
                return Response({"detail": "Активное приглашение не найдено"}, status=404)
            except CallConflict as error:
                return Response({"detail": str(error)}, status=409)
            return Response({"ok": True})


class WidgetLoaderView(View):
    def get(self, request) -> HttpResponse:
        response = HttpResponse(LOADER_JS, content_type="application/javascript; charset=utf-8")
        response["Cache-Control"] = "public, max-age=300"
        return response
