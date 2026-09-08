import time
from urllib.parse import quote

from django.contrib.auth import login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from chatballs.identity.audit import record_audit_event
from chatballs.identity.auth.common import _user_payload
from chatballs.identity.auth.totp_utils import (
    TOTP_CHALLENGE_TTL_SECONDS,
    TOTP_ISSUER,
    TOTP_PERIOD_SECONDS,
    TOTP_SESSION_KEY,
    TOTP_STARTED_KEY,
    _ensure_totp_secret,
    accept_totp_code,
)
from chatballs.identity.models import AuditResult, HumanUser
from chatballs.identity.sessions import remember_device


def _drop_challenge(request: Request) -> None:
    request.session.pop(TOTP_SESSION_KEY, None)
    request.session.pop(TOTP_STARTED_KEY, None)


def _challenge_expired(request: Request) -> bool:
    """Начатый вход, к которому не вернулись, перестаёт ждать код."""
    started = request.session.get(TOTP_STARTED_KEY)
    if not isinstance(started, int | float):
        return True
    return time.time() - started > TOTP_CHALLENGE_TTL_SECONDS


class TotpSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        if request.user.totp_enabled:
            return Response({"detail": "TOTP is already enabled"}, status=400)

        secret = _ensure_totp_secret(request.user)
        account_name = request.user.email
        otpauth_url = (
            f"otpauth://totp/{quote(TOTP_ISSUER)}:{quote(account_name)}"
            f"?secret={secret}&issuer={quote(TOTP_ISSUER)}&digits=6&period={TOTP_PERIOD_SECONDS}"
        )
        return Response(
            {
                "secret": secret,
                "otpauthUrl": otpauth_url,
                "accountName": account_name,
                "issuer": TOTP_ISSUER,
                "period": TOTP_PERIOD_SECONDS,
            }
        )


class TotpConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        _ensure_totp_secret(request.user)
        # Тот же приём кода, что и при входе: интервал запоминается, поэтому
        # код, которым включили 2FA, не сработает ещё раз на входе.
        if not accept_totp_code(request.user, str(request.data.get("code", ""))):
            record_audit_event(
                action="identity.totp_setup_failed",
                actor=request.user,
                result=AuditResult.DENIED,
                request=request,
            )
            return Response({"detail": "Invalid TOTP code"}, status=400)

        request.user.totp_enabled = True
        request.user.save(update_fields=["totp_enabled"])
        record_audit_event(
            action="identity.totp_enabled",
            actor=request.user,
            request=request,
        )
        return Response({"authenticated": True, "user": _user_payload(request.user)})


@method_decorator(csrf_protect, name="dispatch")
class TotpVerifyView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "totp"

    def post(self, request: Request) -> Response:
        pending_user_id = request.session.get(TOTP_SESSION_KEY)
        if not pending_user_id or _challenge_expired(request):
            _drop_challenge(request)
            return Response({"detail": "TOTP challenge is not active"}, status=401)

        try:
            # is_active обязателен: пароль приняли раньше, и без этой проверки
            # отключённый между шагами сотрудник всё равно вошёл бы.
            user = HumanUser.objects.prefetch_related("memberships__organization").get(
                id=pending_user_id, is_active=True
            )
        except HumanUser.DoesNotExist:
            _drop_challenge(request)
            return Response({"detail": "TOTP challenge is not active"}, status=401)

        if not user.totp_enabled or not accept_totp_code(
            user, str(request.data.get("code", ""))
        ):
            record_audit_event(
                action="identity.totp_verify_failed",
                actor=user,
                result=AuditResult.DENIED,
                request=request,
            )
            return Response({"detail": "Invalid TOTP code"}, status=400)

        # Отметку «последний код принят …» для карточки 2FA (кадр P1) уже
        # проставил accept_totp_code вместе с номером интервала.
        _drop_challenge(request)
        login(request, user)
        remember_device(request)
        record_audit_event(
            action="identity.login_succeeded",
            actor=user,
            request=request,
        )
        return Response({"authenticated": True, "user": _user_payload(user)})
