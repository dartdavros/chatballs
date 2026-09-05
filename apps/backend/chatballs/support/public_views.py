from django.db import models
from django.http import FileResponse
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.conversations.attachment_views import attachment_response, validate_upload
from chatballs.conversations.models import Conversation, Message, MessageKind
from chatballs.conversations.serializers import conversation_payload
from chatballs.conversations.transports.base import guess_content_type, safe_filename
from chatballs.conversations.voice_views import ALLOWED_AUDIO_TYPES, MAX_VOICE_BYTES
from chatballs.integrations.features import features_payload, voice_messages_allowed
from chatballs.identity.models import Organization
from chatballs.support import errors
from chatballs.support.messages import post_support_file, post_support_message, post_support_voice, support_messages_since
from chatballs.support.serializers import support_identity_snapshot_payload
from chatballs.support.session import start_support_session
from chatballs.support.token import verify_support_token
from chatballs.support.widget_credential import verify_widget_credential
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import (
    support_channel_routes,
    support_conversation_route,
    web_widget_route,
)
from chatballs.webchat.models import (
    WebChatWidget,
    WebChatWidgetMode,
    WebChatWidgetStatus,
)
from chatballs.webchat.services import origin_allowed


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
                # Что разрешено в этой точке входа: виджет прячет микрофон при запрете.
                "features": features_payload(widget.integration),
            },
            status=201,
        )


def _widget_context(request: Request):
    auth = request.headers.get("Authorization", "")
    # <audio src>/<img src> не умеют заголовки — credential может прийти параметром.
    credential = auth[7:] if auth.startswith("Bearer ") else (request.GET.get("credential", "") if request.method == "GET" else "")
    if not credential:
        return None
    claims = verify_widget_credential(credential)
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
    # JSON — текст, multipart — голосовое или файл.
    parser_classes = [JSONParser, MultiPartParser, FormParser]

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
        audio = request.FILES.get("audio")
        upload = request.FILES.get("file")
        if not text and audio is None and upload is None:
            return Response({"detail": "Пустое сообщение"}, status=400)
        context, claims = resolved
        with tenant_atomic(context):
            conversation = _resolve_widget_conversation(context, claims)
            if conversation is None:
                return Response({"detail": "Сессия не найдена"}, status=401)
            if audio is not None:
                if not voice_messages_allowed(conversation.connection):
                    return Response({"detail": "Голосовые отключены"}, status=400)
                if audio.size > MAX_VOICE_BYTES:
                    return Response({"detail": "Аудио больше 10 МБ"}, status=400)
                content_type = (audio.content_type or "audio/webm").split(";")[0]
                if content_type not in ALLOWED_AUDIO_TYPES:
                    return Response({"detail": "Неподдерживаемый формат аудио"}, status=400)
                try:
                    duration = max(0, int(request.data.get("duration", 0)))
                except (TypeError, ValueError):
                    duration = 0
                post_support_voice(context=context, conversation=conversation, content=audio.read(), content_type=content_type, duration=duration)
                return Response({"ok": True}, status=201)
            if upload is not None:
                problem = validate_upload(upload)
                if problem:
                    return Response({"detail": problem}, status=400)
                name = safe_filename(upload.name or "")
                post_support_file(
                    context=context,
                    conversation=conversation,
                    content=upload.read(),
                    filename=name,
                    content_type=(upload.content_type or "").split(";")[0] or guess_content_type(name),
                    caption=text[:4000],
                )
                return Response({"ok": True}, status=201)
            post_support_message(
                context=context,
                conversation=conversation,
                text=text[:4000],
            )
            return Response({"ok": True}, status=201)


def _session_message(request: Request, message_id: int, kind: str):
    resolved = _widget_context(request)
    if resolved is None:
        return None, Response({"detail": "Сессия не найдена"}, status=401)
    context, claims = resolved
    with tenant_atomic(context):
        conversation = _resolve_widget_conversation(context, claims)
        if conversation is None:
            return None, Response({"detail": "Сессия не найдена"}, status=401)
        message = Message.objects.filter(id=message_id, conversation=conversation, kind=kind).first()
    if message is None:
        return None, Response({"detail": "Сообщение не найдено"}, status=404)
    return (context, message), None


class SupportSessionAudioView(_Public):
    def get(self, request: Request, message_id: int) -> Response | FileResponse:
        found, error = _session_message(request, message_id, MessageKind.VOICE)
        if error is not None:
            return error
        context, message = found
        if not message.audio:
            return Response({"detail": "Аудио недоступно"}, status=404)
        with tenant_atomic(context):
            response = FileResponse(message.audio.open("rb"), content_type=message.audio_content_type or "audio/ogg")
        response["Cache-Control"] = "private, max-age=3600"
        return response


class SupportSessionAttachmentView(_Public):
    def get(self, request: Request, message_id: int) -> Response | FileResponse:
        found, error = _session_message(request, message_id, MessageKind.FILE)
        if error is not None:
            return error
        context, message = found
        if not message.attachment:
            return Response({"detail": "Файл недоступен"}, status=404)
        with tenant_atomic(context):
            response = attachment_response(message, inline="inline" in request.GET)
        response["Cache-Control"] = "private, max-age=3600"
        return response


def _denied() -> Response:
    return Response(
        {
            "error": "support_unavailable",
            "message": errors.PUBLIC_SUPPORT_UNAVAILABLE,
        },
        status=422,
    )
