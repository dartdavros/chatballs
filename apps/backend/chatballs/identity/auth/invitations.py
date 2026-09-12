from __future__ import annotations

from django.contrib.auth import login
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from chatballs.i18n import t
from chatballs.identity.auth.common import _user_payload, validation_response
from chatballs.identity.invitation_service import (
    InvitationError,
    accept_invitation,
    invitation_preview,
    register_and_accept,
)
from chatballs.identity.sessions import remember_device


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InvitationPreviewView(APIView):
    """Что стоит за ссылкой /join до входа: организация, адрес, есть ли учётная запись.

    Ответ нужен экрану, чтобы решить, показать вход или форму создания пароля.
    Токен — секрет из письма, поэтому подробности отдаются только по нему.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def get(self, request: Request) -> Response:
        token = str(request.query_params.get("token", "")).strip()
        preview = invitation_preview(token) if token else None
        if preview is None:
            return Response({"valid": False})
        return Response({"valid": True, **preview})


@method_decorator(csrf_protect, name="dispatch")
class InvitationRegisterView(APIView):
    """Создать учётную запись по приглашению, принять его и войти."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        token = str(body.get("token", "")).strip()
        if not token:
            return Response({"detail": t("identity.token_required")}, status=400)
        try:
            accepted = register_and_accept(
                token=token,
                full_name=str(body.get("fullName", "")),
                password=str(body.get("password", "")),
            )
        except InvitationError as error:
            return Response({"detail": str(error), "code": error.code}, status=400)
        except ValidationError as error:
            return validation_response(error)
        user = accepted.membership.user
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)
        remember_device(request)
        return Response(
            {
                "authenticated": True,
                "user": _user_payload(user),
                "organizationPublicId": str(accepted.organization.public_id),
            },
            status=201,
        )


class InvitationAcceptView(APIView):
    """Accept an organization invitation: OWNER (SPEC-HUB-0021 §8.2) or employee.

    Authenticated endpoint: the caller must already have a HumanUser account
    (created through sign-up / password setup). The token is read from the body;
    on success the response returns the standard user payload so the SPA can
    refresh its membership list.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        token = str(request.data.get("token", "")).strip()
        if not token:
            return Response({"detail": t("identity.token_required")}, status=400)
        try:
            accepted = accept_invitation(token=token, user=request.user)
        except InvitationError as error:
            return Response({"detail": str(error)}, status=400)
        return Response(
            {
                "user": _user_payload(request.user),
                # Куда открыть приложение после принятия.
                "organizationPublicId": str(accepted.organization.public_id),
            }
        )
