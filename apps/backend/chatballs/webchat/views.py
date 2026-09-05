from contextlib import contextmanager

from django.http import FileResponse, HttpResponse
from django.views import View
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.conversations.models import Message, MessageKind
from chatballs.conversations.voice_views import ALLOWED_AUDIO_TYPES, MAX_VOICE_BYTES
from chatballs.identity.models import Organization
from chatballs.integrations.models import IntegrationStatus
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import (
    web_channel_route,
    web_session_route,
    web_widget_route,
)
from chatballs.webchat import services
from chatballs.webchat.loader import LOADER_JS
from chatballs.webchat.models import (
    WebChatWidget,
    WebChatWidgetMode,
    WebChatWidgetStatus,
)


def _origin(request: Request) -> str:
    explicit = (
        request.data.get("hostOrigin", "")
        if request.method == "POST"
        else request.GET.get("hostOrigin", "")
    )
    return str(explicit or request.headers.get("Origin") or request.headers.get("Referer") or "")


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
def _resolved_web_widget(widget_key: str, channel_code: str = ""):
    route = web_widget_route(widget_key) if widget_key else web_channel_route(channel_code)
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
        filters = (
            {"id": route.resource_id, "public_key": widget_key}
            if widget_key
            else {"integration_id": route.resource_id}
        )
        widget = WebChatWidget.objects.select_related(
            "integration",
            "integration__channel",
        ).filter(
            **filters,
            organization=organization,
            status=WebChatWidgetStatus.PUBLISHED,
            integration__organization=organization,
            integration__provider="WEB",
            integration__status=IntegrationStatus.OK,
            integration__is_active=True,
            integration__channel__organization=organization,
            integration__channel__is_active=True,
        ).first()
        if widget is not None and channel_code and widget.integration.channel.code != channel_code:
            widget = None
        yield context, widget


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
        widget_key = request.GET.get("widgetKey", "")
        channel_code = request.GET.get("channel", "")
        with _resolved_web_widget(widget_key, channel_code) as (context, widget):
            if context is None or widget is None:
                return Response({"available": False})
            return Response(
                services.public_config(
                    context=context,
                    widget=widget,
                    origin=_origin(request),
                )
            )


class WebchatSessionView(_Public):
    def post(self, request: Request) -> Response:
        widget_key = str(request.data.get("widgetKey", ""))
        channel_code = str(request.data.get("channel", ""))
        with _resolved_web_widget(widget_key, channel_code) as (context, widget):
            if context is None or widget is None:
                return Response({"detail": "Виджет недоступен"}, status=404)
            if (
                widget.mode != WebChatWidgetMode.ANONYMOUS
                or widget.integration.channel.requires_authenticated_product_identity
                or not widget.integration.channel.allow_anonymous_sessions
                or not services.origin_allowed(widget, _origin(request))
            ):
                return Response({"detail": "Виджет недоступен"}, status=404)
            result = services.issue_session(context=context, widget=widget)
            if result is None:
                return Response({"detail": "Виджет недоступен"}, status=404)
            return Response(result, status=201)


class WebchatMessagesView(_Public):
    # JSON — текст, multipart — голосовое из записи в виджете.
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request: Request) -> Response:
        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": "Сессия не найдена"}, status=401)
            upload = request.FILES.get("audio")
            if upload is not None:
                # Голосовое из виджета (дизайн-базлайн v2, кадр H).
                if upload.size > MAX_VOICE_BYTES:
                    return Response({"detail": "Аудио больше 10 МБ"}, status=400)
                content_type = (upload.content_type or "audio/webm").split(";")[0]
                if content_type not in ALLOWED_AUDIO_TYPES:
                    return Response({"detail": "Неподдерживаемый формат аудио"}, status=400)
                try:
                    duration = max(0, int(request.data.get("duration", 0)))
                except (TypeError, ValueError):
                    duration = 0
                services.post_voice(
                    session,
                    content=upload.read(),
                    content_type=content_type,
                    duration=duration,
                )
                return Response({"ok": True}, status=201)
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


class WebchatMessageAudioView(_Public):
    def get(self, request: Request, message_id: int) -> Response | FileResponse:
        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": "Сессия не найдена"}, status=401)
            message = (
                Message.objects.filter(
                    id=message_id,
                    kind=MessageKind.VOICE,
                    conversation__channel=session.connection.channel,
                    conversation__contact=session.identity.contact,
                )
                .exclude(audio="")
                .first()
            )
            if message is None:
                return Response({"detail": "Сообщение не найдено"}, status=404)
            response = FileResponse(
                message.audio.open("rb"),
                content_type=message.audio_content_type or "audio/ogg",
            )
            response["Cache-Control"] = "private, max-age=3600"
            return response


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
        from chatballs.calls.errors import CallTokenError
        from chatballs.calls.serializers import ice_servers_payload, public_invite_payload
        from chatballs.calls.services import open_call_for_identity

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
        from chatballs.calls.errors import CallConflict, CallTokenError
        from chatballs.calls.services import decline_call_for_identity

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
