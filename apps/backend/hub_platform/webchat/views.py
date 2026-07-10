from django.http import HttpResponse
from django.views import View
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

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


class WebchatConfigView(_Public):
    def get(self, request: Request) -> Response:
        return Response(services.public_config(request.GET.get("channel", ""), _origin(request)))


class WebchatSessionView(_Public):
    def post(self, request: Request) -> Response:
        result = services.issue_session(str(request.data.get("channel", "")))
        if result is None:
            return Response({"detail": "Канал недоступен"}, status=404)
        return Response(result, status=201)


class WebchatMessagesView(_Public):
    def post(self, request: Request) -> Response:
        session = services.resolve_session(_token(request))
        if session is None:
            return Response({"detail": "Сессия не найдена"}, status=401)
        text = str(request.data.get("text", "")).strip()
        if not text:
            return Response({"detail": "Пустое сообщение"}, status=400)
        services.post_message(session, text[:4000])
        return Response({"ok": True}, status=201)

    def get(self, request: Request) -> Response:
        session = services.resolve_session(_token(request))
        if session is None:
            return Response({"detail": "Сессия не найдена"}, status=401)
        try:
            since = int(request.GET.get("since", "0") or 0)
        except ValueError:
            since = 0
        return Response(services.messages_payload(session, since))


class WebchatContactView(_Public):
    def post(self, request: Request) -> Response:
        session = services.resolve_session(_token(request))
        if session is None:
            return Response({"detail": "Сессия не найдена"}, status=401)
        phone = services.normalize_phone(str(request.data.get("phone", "")))
        if not phone:
            return Response({"detail": "Некорректный номер телефона"}, status=400)
        services.post_contact(session, phone)
        return Response({"ok": True}, status=201)


class WidgetLoaderView(View):
    def get(self, request) -> HttpResponse:
        response = HttpResponse(LOADER_JS, content_type="application/javascript; charset=utf-8")
        response["Cache-Control"] = "public, max-age=300"
        return response
