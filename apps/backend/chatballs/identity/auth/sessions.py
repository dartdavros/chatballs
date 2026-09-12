import time

from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from chatballs.i18n import current_language, t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.auth.common import _challenge_payload, _user_payload
from chatballs.identity.auth.totp_utils import TOTP_SESSION_KEY, TOTP_STARTED_KEY
from chatballs.identity.models import AuditResult
from chatballs.identity.sessions import remember_device


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            # Язык установки нужен и до входа: логин и сброс пароля — экраны
            # самой коробки, и на английской машине они должны открываться на
            # языке установки, а не на языке браузера. Без этого фронтенд знал
            # бы только про браузер и расходился бы с бэкендом, который язык
            # установки учитывает.
            return Response({"authenticated": False, "language": current_language()})
        return Response({"authenticated": True, "user": _user_payload(request.user)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request: Request) -> Response:
        body = request.data
        email = str(body.get("email", ""))
        password = str(body.get("password", ""))
        request.session.pop(TOTP_SESSION_KEY, None)
        request.session.pop(TOTP_STARTED_KEY, None)
        user = authenticate(request, username=email, password=password)
        if user is None:
            record_audit_event(action="identity.login_failed", result=AuditResult.DENIED, request=request)
            return Response({"detail": t("identity.invalid_credentials")}, status=401)
        if user.totp_enabled:
            request.session[TOTP_SESSION_KEY] = user.id
            # Шаг с кодом ждёт не вечно: см. TOTP_CHALLENGE_TTL_SECONDS.
            request.session[TOTP_STARTED_KEY] = time.time()
            record_audit_event(
                action="identity.login_totp_required",
                actor=user,
                request=request,
            )
            return Response(
                {
                    "authenticated": False,
                    "totpRequired": True,
                    "totpEnabled": True,
                    "challenge": _challenge_payload(user),
                }
            )

        login(request, user)
        remember_device(request)
        record_audit_event(
            action="identity.login_succeeded",
            actor=user,
            request=request,
        )
        return Response({"authenticated": True, "user": _user_payload(user)})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        user = request.user
        logout(request)
        record_audit_event(action="identity.logout", actor=user, request=request)
        return Response({"authenticated": False})
