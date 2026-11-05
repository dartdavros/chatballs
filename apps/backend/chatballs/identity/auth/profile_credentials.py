"""Existing interactive password and TOTP ceremonies; never native actions."""
from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.auth.common import _revoke_other_user_sessions, _user_payload
from chatballs.tenancy.ingress import user_requires_totp


class ProfilePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        body = request.data
        current_password = str(body.get("currentPassword", ""))
        new_password = str(body.get("newPassword", ""))
        if not request.user.check_password(current_password):
            return Response({"detail": t("profile.current_password_invalid")}, status=400)
        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as error:
            return Response({"detail": " ".join(error.messages)}, status=400)

        request.user.set_password(new_password)
        request.user.password_changed_at = timezone.now()
        request.user.save(update_fields=["password", "password_changed_at"])
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
    """Начало настройки 2FA: выдать пользователю новый секрет.

    Выключать этим уже включённую 2FA нельзя. Иначе достаточно было бы
    угнанной сессии: отключение (``ProfileTotpDisableView``) спрашивает
    текущий пароль и не даёт обойти требование организации, а этот эндпоинт
    молча делал ровно то же самое без единой проверки.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if request.user.totp_enabled:
            return Response(
                {"detail": t("profile.totp_already_on")},
                status=409,
            )
        request.user.totp_secret = ""
        request.user.save(update_fields=["totp_secret"])
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
            return Response({"detail": t("profile.current_password_invalid")}, status=400)

        if user_requires_totp(request.user.id):
            return Response({"detail": t("profile.totp_required_by_policy")}, status=409)
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


class ChangeTemporaryPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        body = request.data
        current_password = str(body.get("currentPassword", ""))
        new_password = str(body.get("newPassword", ""))
        if not request.user.must_change_password and not request.user.check_password(current_password):
            return Response({"detail": t("profile.current_password_invalid")}, status=400)
        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as error:
            return Response({"detail": " ".join(error.messages)}, status=400)

        request.user.set_password(new_password)
        request.user.must_change_password = False
        request.user.password_changed_at = timezone.now()
        request.user.save(update_fields=["password", "must_change_password", "password_changed_at"])
        login(request, request.user)
        record_audit_event(
            action="identity.temporary_password_changed",
            actor=request.user,
            request=request,
        )
        return Response({"authenticated": True, "user": _user_payload(request.user)})
