from urllib.parse import quote

from django.contrib.auth import login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.auth.common import _user_payload
from hub_platform.identity.auth.totp_utils import (
    TOTP_ISSUER,
    TOTP_PERIOD_SECONDS,
    TOTP_SESSION_KEY,
    _ensure_totp_secret,
    _verify_totp,
)
from hub_platform.identity.models import AuditResult, HumanUser


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
        secret = _ensure_totp_secret(request.user)
        if not _verify_totp(secret, str(request.data.get("code", ""))):
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
        if not pending_user_id:
            return Response({"detail": "TOTP challenge is not active"}, status=401)

        try:
            user = HumanUser.objects.prefetch_related("memberships__organization").get(
                id=pending_user_id
            )
        except HumanUser.DoesNotExist:
            request.session.pop(TOTP_SESSION_KEY, None)
            return Response({"detail": "TOTP challenge is not active"}, status=401)

        if (
            not user.totp_enabled
            or not user.totp_secret
            or not _verify_totp(user.totp_secret, str(request.data.get("code", "")))
        ):
            record_audit_event(
                action="identity.totp_verify_failed",
                actor=user,
                result=AuditResult.DENIED,
                request=request,
            )
            return Response({"detail": "Invalid TOTP code"}, status=400)

        request.session.pop(TOTP_SESSION_KEY, None)
        login(request, user)
        record_audit_event(
            action="identity.login_succeeded",
            actor=user,
            request=request,
        )
        return Response({"authenticated": True, "user": _user_payload(user)})
