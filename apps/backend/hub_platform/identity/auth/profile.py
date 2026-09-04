from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.auth.common import _revoke_other_user_sessions, _user_payload
from hub_platform.tenancy.ingress import user_requires_totp
from hub_platform.identity.models import HumanUser


class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        body = request.data
        full_name = str(body.get("fullName", "")).strip()
        email = HumanUser.objects.normalize_email(str(body.get("email", "")).strip())
        if not full_name:
            return Response({"detail": "Full name is required"}, status=400)
        if not email:
            return Response({"detail": "Email is required"}, status=400)
        if HumanUser.objects.exclude(id=request.user.id).filter(email=email).exists():
            return Response({"detail": "Email is already used"}, status=400)

        request.user.full_name = full_name
        request.user.email = email
        request.user.save(update_fields=["full_name", "email"])
        record_audit_event(
            action="identity.profile_updated",
            actor=request.user,
            object_type="HumanUser",
            object_id=str(request.user.id),
            request=request,
        )
        return Response({"authenticated": True, "user": _user_payload(request.user)})


class ProfilePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        body = request.data
        current_password = str(body.get("currentPassword", ""))
        new_password = str(body.get("newPassword", ""))
        if not request.user.check_password(current_password):
            return Response({"detail": "Current password is invalid"}, status=400)
        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as error:
            return Response({"detail": " ".join(error.messages)}, status=400)

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])
        login(request, request.user)
        revoked = _revoke_other_user_sessions(request)
        record_audit_event(
            action="identity.profile_password_changed",
            actor=request.user,
            payload={"revoked": revoked},
            request=request,
        )
        return Response({"authenticated": True, "user": _user_payload(request.user), "revoked": revoked})


class ProfileTotpStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        request.user.totp_enabled = False
        request.user.totp_secret = ""
        request.user.save(update_fields=["totp_enabled", "totp_secret"])
        record_audit_event(
            action="identity.profile_totp_setup_started",
            actor=request.user,
            request=request,
        )
        return Response({"authenticated": True, "user": _user_payload(request.user)})


class ProfileTotpDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        current_password = str(request.data.get("currentPassword", ""))
        if not request.user.check_password(current_password):
            return Response({"detail": "Current password is invalid"}, status=400)

        if user_requires_totp(request.user.id):
            return Response({"detail": "TOTP is required by an organization policy"}, status=409)
        request.user.totp_enabled = False
        request.user.totp_secret = ""
        request.user.save(update_fields=["totp_enabled", "totp_secret"])
        revoked = _revoke_other_user_sessions(request)
        record_audit_event(
            action="identity.profile_totp_disabled",
            actor=request.user,
            payload={"revoked": revoked},
            request=request,
        )
        return Response({"authenticated": True, "user": _user_payload(request.user), "revoked": revoked})


class ProfileRevokeOtherSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        revoked = _revoke_other_user_sessions(request)
        record_audit_event(
            action="identity.profile_sessions_revoked",
            actor=request.user,
            payload={"revoked": revoked},
            request=request,
        )
        return Response({"revoked": revoked})


class ChangeTemporaryPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        body = request.data
        current_password = str(body.get("currentPassword", ""))
        new_password = str(body.get("newPassword", ""))
        if not request.user.must_change_password and not request.user.check_password(current_password):
            return Response({"detail": "Current password is invalid"}, status=400)
        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as error:
            return Response({"detail": " ".join(error.messages)}, status=400)

        request.user.set_password(new_password)
        request.user.must_change_password = False
        request.user.save(update_fields=["password", "must_change_password"])
        login(request, request.user)
        record_audit_event(
            action="identity.temporary_password_changed",
            actor=request.user,
            request=request,
        )
        return Response({"authenticated": True, "user": _user_payload(request.user)})


class ProfileAppearanceView(APIView):
    """Тема и акцентный цвет — глобальные настройки пользователя
    (SPEC-HUB-0031 §7, дизайн-базлайн v2)."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        import re

        from hub_platform.identity.models import UiTheme

        body = request.data
        theme = str(body.get("theme", request.user.ui_theme)).strip().upper()
        accent = str(body.get("accent", request.user.ui_accent)).strip().lower()
        if theme not in UiTheme.values:
            return Response({"detail": "Неизвестная тема"}, status=400)
        if accent and not re.fullmatch(r"#[0-9a-f]{6}", accent):
            return Response({"detail": "Акцент — HEX-цвет вида #1677ff"}, status=400)
        request.user.ui_theme = theme
        request.user.ui_accent = accent
        request.user.save(update_fields=["ui_theme", "ui_accent"])
        return Response({"authenticated": True, "user": _user_payload(request.user)})
