from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse
from django.utils import timezone, translation
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.i18n import t
from chatballs.i18n.languages import normalize_language, resolve_language
from chatballs.identity.audit import record_audit_event
from chatballs.identity.auth.common import _revoke_other_user_sessions, _user_payload
from chatballs.identity.avatars import delete_user_avatar, replace_user_avatar
from chatballs.identity.instance_settings import default_language
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.identity.sessions import list_user_sessions
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import membership_routes_for_user, user_requires_totp


class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        body = request.data
        full_name = str(body.get("fullName", "")).strip()
        email = HumanUser.objects.normalize_email(str(body.get("email", "")).strip())
        if not full_name:
            return Response({"detail": t("admin.full_name_required")}, status=400)
        if not email:
            return Response({"detail": t("admin.email_required")}, status=400)
        if HumanUser.objects.exclude(id=request.user.id).filter(email=email).exists():
            return Response({"detail": t("admin.email_taken")}, status=400)

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


class ProfileAvatarView(APIView):
    """Фото профиля: показать, заменить, удалить (дизайн-базлайн v2)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request: Request) -> Response | FileResponse:
        user = request.user
        if not user.avatar:
            return Response({"detail": t("profile.photo_not_set")}, status=404)
        return FileResponse(
            user.avatar.open("rb"),
            content_type=user.avatar_content_type or "application/octet-stream",
            filename="avatar",
        )

    def post(self, request: Request) -> Response:
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": t("profile.choose_photo_file")}, status=400)
        replace_user_avatar(request.user, upload)
        record_audit_event(
            action="identity.avatar_updated",
            actor=request.user,
            object_type="HumanUser",
            object_id=str(request.user.id),
            request=request,
        )
        return Response({"authenticated": True, "user": _user_payload(request.user)})

    def delete(self, request: Request) -> Response:
        delete_user_avatar(request.user)
        record_audit_event(
            action="identity.avatar_deleted",
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


class ProfileSessionsView(APIView):
    """Список активных сессий учётной записи (кадр P1)."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        items = list_user_sessions(request.user.id, request.session.session_key)
        return Response({"items": items})


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


class ProfileAppearanceView(APIView):
    """Тема и акцентный цвет — глобальные настройки пользователя
    (SPEC-CHATBALLS-0031 §7, дизайн-базлайн v2)."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        import re

        from chatballs.identity.models import UiTheme

        body = request.data
        theme = str(body.get("theme", request.user.ui_theme)).strip().upper()
        accent = str(body.get("accent", request.user.ui_accent)).strip().lower()
        if theme not in UiTheme.values:
            return Response({"detail": t("profile.unknown_theme")}, status=400)
        if accent and not re.fullmatch(r"#[0-9a-f]{6}", accent):
            return Response({"detail": t("profile.accent_hex")}, status=400)
        request.user.ui_theme = theme
        request.user.ui_accent = accent
        request.user.save(update_fields=["ui_theme", "ui_accent"])
        return Response({"authenticated": True, "user": _user_payload(request.user)})


class ProfileLanguageView(APIView):
    """Язык интерфейса — личная настройка сотрудника.

    Пустое значение возвращает человека к языку организации: это не «русский»,
    а снятие личного выбора, и после смены языка организации такой сотрудник
    поедет за ней, а тот, кто выбрал язык явно, — нет.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        raw = str(request.data.get("language", "")).strip()
        language = normalize_language(raw)
        if raw and not language:
            return Response({"detail": t("settings.language_unsupported")}, status=400)
        request.user.ui_language = language
        request.user.save(update_fields=["ui_language"])
        record_audit_event(
            action="identity.profile_language_changed",
            actor=request.user,
            object_type="HumanUser",
            object_id=str(request.user.id),
            request=request,
        )
        # Ответ уже на новом языке: интерфейс перерисуется по нему сразу, не
        # дожидаясь следующего запроса.
        resolved = resolve_language(
            user_language=language,
            organization_language=_request_organization_language(request),
            instance_language=default_language(),
            accept_language=request.headers.get("Accept-Language"),
        )
        with translation.override(resolved):
            return Response({"authenticated": True, "user": _user_payload(request.user)})


def _request_organization_language(request: Request) -> str:
    """Язык организации запроса, если он у этого запроса вообще есть.

    Профиль открывается вне организации, поэтому tenant_context здесь обычно
    пуст: тогда язык берётся из единственного членства, а при нескольких —
    из того, что старше, чтобы ответ не зависел от порядка выборки.
    """

    context = getattr(request, "tenant_context", None)
    if context is not None:
        return context.organization.language or ""
    # Членства роли app без контекста не видны: сначала каталог входа, затем
    # каждое членство читается в контексте своей организации — как в
    # identity.auth.common._user_payload.
    oldest: tuple[object, int, str] | None = None
    for route in membership_routes_for_user(request.user.id):
        with tenant_atomic(route.organization_id):
            membership = (
                OrganizationMembership.objects.select_related("organization")
                .filter(id=route.resource_id, user=request.user, blocked_at__isnull=True)
                .first()
            )
        if membership is None:
            continue
        key = (membership.created_at, membership.id, membership.organization.language or "")
        if oldest is None or key[:2] < oldest[:2]:
            oldest = key
    return oldest[2] if oldest is not None else ""
