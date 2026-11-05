from django.http import FileResponse
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.conversations.attachment_views import (
    attachment_response,
    validate_upload,
)
from chatballs.conversations.models import MessageKind
from chatballs.i18n import t
from chatballs.webchat import services
from chatballs.webchat.access import (
    _Public,
    _PublicSession,
    _resolved_web_session,
    _resolved_web_widget,
)
from chatballs.webchat.api_inputs import host_origin
from chatballs.webchat.message_selectors import session_messages
from chatballs.webchat.throttling import (
    WebchatSessionIssueThrottle,
)


class WebchatSessionView(_Public):
    throttle_classes = [WebchatSessionIssueThrottle]

    def post(self, request: Request) -> Response:
        widget_key = str(request.data.get("widgetKey", ""))
        channel_code = str(request.data.get("channel", ""))
        with _resolved_web_widget(widget_key, channel_code) as (context, widget):
            if context is None or widget is None:
                return Response({"detail": t("webchat.widget_unavailable")}, status=404)
            if (
                not widget.integration.channel.allow_anonymous_sessions
                or not services.origin_allowed(widget, host_origin(request))
            ):
                return Response({"detail": t("webchat.widget_unavailable")}, status=404)
            result = services.issue_session(
                context=context, widget=widget, fields=request.data.get("fields"),
                pre_chat_fields=request.data.get("preChatFields"),
                consent_version=request.data.get("consentVersion"),
            )
            if result is None:
                return Response({"detail": t("webchat.widget_unavailable")}, status=404)
            return Response(result, status=201)


class WebchatFieldsView(_PublicSession):
    def post(self, request: Request) -> Response:
        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            from chatballs.webchat.site_fields import save_site_fields

            save_site_fields(session, request.data.get("fields"))
            return Response({"ok": True})


class WebchatMessagesView(_PublicSession):
    # JSON — текст, multipart — голосовое из записи в виджете.
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request: Request) -> Response:
        if (request.content_type or "").startswith("multipart/form-data") and request.FILES.get("audio") is not None:
            from chatballs.webchat.voice_inputs import post_web_voice

            return post_web_voice(request, request.FILES["audio"])
        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            attachment = request.FILES.get("file")
            if attachment is not None:
                problem = validate_upload(attachment)
                if problem:
                    return Response({"detail": problem}, status=400)
                services.post_file(
                    session,
                    content=attachment.read(),
                    filename=attachment.name or "file",
                    content_type=(attachment.content_type or "").split(";")[0],
                    caption=str(request.data.get("text", "")).strip()[:4000],
                )
                return Response({"ok": True}, status=201)
            text = str(request.data.get("text", "")).strip()
            if not text:
                return Response({"detail": t("ai.empty_message")}, status=400)
            if len(text) > 4000:
                return Response({"detail": t("speech.text_too_long")}, status=400)
            services.post_message(session, text)
            return Response({"ok": True}, status=201)

    def get(self, request: Request) -> Response:
        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            try:
                since = int(request.GET.get("since", "0") or 0)
            except ValueError:
                since = 0
            return Response(services.messages_payload(session, since))


class WebchatMessageAudioView(_PublicSession):
    def get(self, request: Request, message_id: int) -> Response | FileResponse:
        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            message = (
                session_messages(session).filter(
                    id=message_id,
                    kind=MessageKind.VOICE,
                )
                .exclude(audio="")
                .first()
            )
            if message is None:
                return Response({"detail": t("conversations.message_not_found")}, status=404)
            response = FileResponse(
                message.audio.open("rb"),
                content_type=message.audio_content_type or "audio/ogg",
            )
            response["Cache-Control"] = "private, max-age=3600"
            return response


class WebchatMessageAttachmentView(_PublicSession):
    def get(self, request: Request, message_id: int) -> Response | FileResponse:
        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            message = (
                session_messages(session).filter(
                    id=message_id,
                    kind=MessageKind.FILE,
                )
                .exclude(attachment="")
                .first()
            )
            if message is None:
                return Response({"detail": t("conversations.message_not_found")}, status=404)
            response = attachment_response(message, inline="inline" in request.GET)
            response["Cache-Control"] = "private, max-age=3600"
            return response


class WebchatContactView(_PublicSession):
    def post(self, request: Request) -> Response:
        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            phone = services.normalize_phone(str(request.data.get("phone", "")))
            if not phone:
                return Response({"detail": t("webchat.invalid_phone")}, status=400)
            services.post_contact(session, phone)
            return Response({"ok": True}, status=201)


class WebchatCallOpenView(_PublicSession):
    def post(self, request: Request) -> Response:
        from chatballs.calls.errors import CallTokenError
        from chatballs.calls.serializers import (
            ice_servers_payload,
            public_invite_payload,
        )
        from chatballs.calls.services import open_call_for_identity

        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            try:
                resolved = open_call_for_identity(identity=session.identity)
            except CallTokenError:
                return Response({"detail": t("webchat.no_active_invite")}, status=404)
            response = Response(
                {
                    "call": public_invite_payload(resolved.invite.call_session, resolved.invite.expires_at),
                    "accessToken": resolved.customer_access_token,
                    "iceServers": ice_servers_payload(),
                }
            )
            response["Cache-Control"] = "no-store"
            return response


class WebchatCallDeclineView(_PublicSession):
    def post(self, request: Request) -> Response:
        from chatballs.calls.errors import CallConflict, CallTokenError
        from chatballs.calls.services import decline_call_for_identity

        with _resolved_web_session(request) as (_context, session):
            if session is None:
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            try:
                decline_call_for_identity(identity=session.identity)
            except CallTokenError:
                return Response({"detail": t("webchat.no_active_invite")}, status=404)
            except CallConflict as error:
                return Response({"detail": str(error)}, status=409)
            return Response({"ok": True})
