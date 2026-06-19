import base64
import hashlib
import hmac
import json
import os
import struct
import time
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.http import HttpRequest, JsonResponse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import AuditResult, HumanUser

TOTP_SESSION_KEY = "identity_pending_totp_user_id"
TOTP_ISSUER = "Edevs Hub"
TOTP_PERIOD_SECONDS = 30


def _json_body(request: HttpRequest) -> dict[str, object]:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def _user_payload(user: HumanUser) -> dict[str, object]:
    profile = user.employee_profile
    return {
        "id": user.id,
        "email": user.email,
        "fullName": user.full_name,
        "role": profile.role,
        "organizationName": profile.organization.name,
        "organization": profile.organization.slug,
        "department": profile.department.code if profile.department else None,
        "mustChangePassword": profile.must_change_password,
        "totpRequired": profile.totp_required,
        "totpEnabled": profile.totp_enabled,
    }


def _challenge_payload(user: HumanUser) -> dict[str, object]:
    profile = user.employee_profile
    return {
        "email": user.email,
        "fullName": user.full_name,
        "role": profile.role,
    }


def _generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")


def _decode_totp_secret(secret: str) -> bytes:
    normalized = secret.strip().replace(" ", "").upper()
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    return base64.b32decode(normalized + padding)


def _totp_code(secret: str, for_time: int | None = None) -> str:
    timestamp = int(time.time() if for_time is None else for_time)
    counter = timestamp // TOTP_PERIOD_SECONDS
    digest = hmac.new(_decode_totp_secret(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1_000_000:06d}"


def _verify_totp(secret: str, code: str) -> bool:
    normalized = "".join(character for character in code if character.isdigit())
    if len(normalized) != 6:
        return False
    now = int(time.time())
    return any(
        hmac.compare_digest(_totp_code(secret, now + (offset * TOTP_PERIOD_SECONDS)), normalized)
        for offset in (-1, 0, 1)
    )


def _ensure_totp_secret(user: HumanUser) -> str:
    profile = user.employee_profile
    if not profile.totp_secret:
        profile.totp_secret = _generate_totp_secret()
        profile.save(update_fields=["totp_secret"])
    return profile.totp_secret


def _revoke_other_user_sessions(request: HttpRequest) -> int:
    current_key = request.session.session_key
    user_id = str(request.user.id)
    revoked = 0
    for session in Session.objects.all():
        if session.session_key == current_key:
            continue
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == user_id:
            session.delete()
            revoked += 1
    return revoked


@ensure_csrf_cookie
@require_GET
def session_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False})
    return JsonResponse({"authenticated": True, "user": _user_payload(request.user)})


@csrf_protect
@require_POST
def login_view(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    email = str(body.get("email", ""))
    password = str(body.get("password", ""))
    request.session.pop(TOTP_SESSION_KEY, None)
    user = authenticate(request, username=email, password=password)
    if user is None:
        record_audit_event(action="identity.login_failed", result=AuditResult.DENIED, request=request)
        return JsonResponse({"detail": "Invalid credentials"}, status=401)
    if not hasattr(user, "employee_profile") or user.employee_profile.is_blocked:
        record_audit_event(action="identity.login_blocked", actor=user, result=AuditResult.DENIED, request=request)
        return JsonResponse({"detail": "Account is blocked"}, status=403)

    profile = user.employee_profile
    if profile.totp_enabled:
        request.session[TOTP_SESSION_KEY] = user.id
        record_audit_event(
            action="identity.login_totp_required",
            actor=user,
            organization=profile.organization,
            request=request,
        )
        return JsonResponse(
            {
                "authenticated": False,
                "totpRequired": True,
                "totpEnabled": True,
                "challenge": _challenge_payload(user),
            }
        )

    login(request, user)
    record_audit_event(
        action="identity.login_succeeded",
        actor=user,
        organization=profile.organization,
        request=request,
    )
    return JsonResponse({"authenticated": True, "user": _user_payload(user)})


@csrf_protect
@require_POST
def logout_view(request: HttpRequest) -> JsonResponse:
    user = request.user if request.user.is_authenticated else None
    organization = getattr(getattr(user, "employee_profile", None), "organization", None)
    logout(request)
    record_audit_event(action="identity.logout", actor=user, organization=organization, request=request)
    return JsonResponse({"authenticated": False})


def _send_password_reset_email(user: HumanUser) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f"{settings.INTERNAL_UI_BASE_URL.rstrip('/')}/reset-password?uid={uid}&token={token}"
    send_mail(
        subject="Восстановление доступа к Edevs Hub",
        message=(
            f"Здравствуйте, {user.full_name or user.email}.\n\n"
            "Вы запросили сброс пароля для Edevs Hub. Чтобы задать новый пароль, перейдите по ссылке:\n"
            f"{reset_url}\n\n"
            "Ссылка действует 30 минут. Если вы не запрашивали сброс, просто проигнорируйте это письмо."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


@csrf_protect
@require_POST
def password_reset_request_view(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    email = HumanUser.objects.normalize_email(str(body.get("email", "")).strip())
    if email:
        user = HumanUser.objects.filter(email__iexact=email, is_active=True).first()
        profile = getattr(user, "employee_profile", None) if user is not None else None
        if user is not None and profile is not None and not profile.is_blocked:
            _send_password_reset_email(user)
            record_audit_event(
                action="identity.password_reset_requested",
                actor=user,
                organization=profile.organization,
                request=request,
            )
        else:
            record_audit_event(
                action="identity.password_reset_requested",
                result=AuditResult.DENIED,
                object_type="email",
                object_id=email,
                request=request,
            )
    # Ответ не зависит от наличия аккаунта — защита от перебора адресов.
    return JsonResponse({"ok": True})


def _user_from_reset_link(uid: str, token: str) -> HumanUser | None:
    try:
        user = HumanUser.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (TypeError, ValueError, OverflowError, HumanUser.DoesNotExist):
        return None
    if not user.is_active or not default_token_generator.check_token(user, token):
        return None
    return user


@require_GET
def password_reset_validate_view(request: HttpRequest) -> JsonResponse:
    user = _user_from_reset_link(request.GET.get("uid", ""), request.GET.get("token", ""))
    return JsonResponse({"valid": user is not None})


@csrf_protect
@require_POST
def password_reset_confirm_view(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    user = _user_from_reset_link(str(body.get("uid", "")), str(body.get("token", "")))
    if user is None:
        record_audit_event(action="identity.password_reset_failed", result=AuditResult.DENIED, request=request)
        return JsonResponse({"detail": "Ссылка недействительна или истекла"}, status=400)

    new_password = str(body.get("newPassword", ""))
    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as error:
        return JsonResponse({"detail": " ".join(error.messages)}, status=400)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    profile = getattr(user, "employee_profile", None)
    if profile is not None and profile.must_change_password:
        profile.must_change_password = False
        profile.save(update_fields=["must_change_password"])
    record_audit_event(
        action="identity.password_reset_completed",
        actor=user,
        organization=profile.organization if profile is not None else None,
        request=request,
    )
    return JsonResponse({"ok": True})


@csrf_protect
@require_POST
def profile_update_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    body = _json_body(request)
    full_name = str(body.get("fullName", "")).strip()
    email = HumanUser.objects.normalize_email(str(body.get("email", "")).strip())
    if not full_name:
        return JsonResponse({"detail": "Full name is required"}, status=400)
    if not email:
        return JsonResponse({"detail": "Email is required"}, status=400)
    if HumanUser.objects.exclude(id=request.user.id).filter(email=email).exists():
        return JsonResponse({"detail": "Email is already used"}, status=400)

    request.user.full_name = full_name
    request.user.email = email
    request.user.save(update_fields=["full_name", "email"])
    profile = request.user.employee_profile
    record_audit_event(
        action="identity.profile_updated",
        actor=request.user,
        organization=profile.organization,
        object_type="HumanUser",
        object_id=str(request.user.id),
        request=request,
    )
    return JsonResponse({"authenticated": True, "user": _user_payload(request.user)})


@csrf_protect
@require_POST
def profile_password_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    body = _json_body(request)
    current_password = str(body.get("currentPassword", ""))
    new_password = str(body.get("newPassword", ""))
    if not request.user.check_password(current_password):
        return JsonResponse({"detail": "Current password is invalid"}, status=400)
    if len(new_password) < 10:
        return JsonResponse({"detail": "Password is too short"}, status=400)

    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])
    login(request, request.user)
    profile = request.user.employee_profile
    revoked = _revoke_other_user_sessions(request)
    record_audit_event(
        action="identity.profile_password_changed",
        actor=request.user,
        organization=profile.organization,
        payload={"revoked": revoked},
        request=request,
    )
    return JsonResponse({"authenticated": True, "user": _user_payload(request.user), "revoked": revoked})


@csrf_protect
@require_POST
def profile_totp_start_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    profile = request.user.employee_profile
    profile.totp_required = True
    profile.totp_enabled = False
    profile.totp_secret = ""
    profile.save(update_fields=["totp_required", "totp_enabled", "totp_secret"])
    record_audit_event(
        action="identity.profile_totp_setup_started",
        actor=request.user,
        organization=profile.organization,
        request=request,
    )
    return JsonResponse({"authenticated": True, "user": _user_payload(request.user)})


@csrf_protect
@require_POST
def profile_totp_disable_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    body = _json_body(request)
    current_password = str(body.get("currentPassword", ""))
    if not request.user.check_password(current_password):
        return JsonResponse({"detail": "Current password is invalid"}, status=400)

    profile = request.user.employee_profile
    profile.totp_required = False
    profile.totp_enabled = False
    profile.totp_secret = ""
    profile.save(update_fields=["totp_required", "totp_enabled", "totp_secret"])
    revoked = _revoke_other_user_sessions(request)
    record_audit_event(
        action="identity.profile_totp_disabled",
        actor=request.user,
        organization=profile.organization,
        payload={"revoked": revoked},
        request=request,
    )
    return JsonResponse({"authenticated": True, "user": _user_payload(request.user), "revoked": revoked})


@csrf_protect
@require_POST
def profile_revoke_other_sessions_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    revoked = _revoke_other_user_sessions(request)
    profile = request.user.employee_profile
    record_audit_event(
        action="identity.profile_sessions_revoked",
        actor=request.user,
        organization=profile.organization,
        payload={"revoked": revoked},
        request=request,
    )
    return JsonResponse({"revoked": revoked})


@csrf_protect
@require_POST
def change_temporary_password_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    body = _json_body(request)
    current_password = str(body.get("currentPassword", ""))
    new_password = str(body.get("newPassword", ""))
    profile = request.user.employee_profile
    if not profile.must_change_password and not request.user.check_password(current_password):
        return JsonResponse({"detail": "Current password is invalid"}, status=400)
    if len(new_password) < 10:
        return JsonResponse({"detail": "Password is too short"}, status=400)

    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])
    profile.must_change_password = False
    profile.save(update_fields=["must_change_password"])
    login(request, request.user)
    record_audit_event(
        action="identity.temporary_password_changed",
        actor=request.user,
        organization=profile.organization,
        request=request,
    )
    return JsonResponse({"authenticated": True, "user": _user_payload(request.user)})


@csrf_protect
@require_GET
def totp_setup_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)
    profile = request.user.employee_profile
    if not profile.totp_required:
        return JsonResponse({"detail": "TOTP is not required"}, status=400)
    if profile.totp_enabled:
        return JsonResponse({"detail": "TOTP is already enabled"}, status=400)

    secret = _ensure_totp_secret(request.user)
    account_name = request.user.email
    otpauth_url = (
        f"otpauth://totp/{quote(TOTP_ISSUER)}:{quote(account_name)}"
        f"?secret={secret}&issuer={quote(TOTP_ISSUER)}&digits=6&period={TOTP_PERIOD_SECONDS}"
    )
    return JsonResponse(
        {
            "secret": secret,
            "otpauthUrl": otpauth_url,
            "accountName": account_name,
            "issuer": TOTP_ISSUER,
            "period": TOTP_PERIOD_SECONDS,
        }
    )


@csrf_protect
@require_POST
def totp_confirm_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)
    profile = request.user.employee_profile
    if not profile.totp_required:
        return JsonResponse({"detail": "TOTP is not required"}, status=400)

    body = _json_body(request)
    secret = _ensure_totp_secret(request.user)
    if not _verify_totp(secret, str(body.get("code", ""))):
        record_audit_event(
            action="identity.totp_setup_failed",
            actor=request.user,
            organization=profile.organization,
            result=AuditResult.DENIED,
            request=request,
        )
        return JsonResponse({"detail": "Invalid TOTP code"}, status=400)

    profile.totp_enabled = True
    profile.save(update_fields=["totp_enabled"])
    record_audit_event(
        action="identity.totp_enabled",
        actor=request.user,
        organization=profile.organization,
        request=request,
    )
    return JsonResponse({"authenticated": True, "user": _user_payload(request.user)})


@csrf_protect
@require_POST
def totp_verify_view(request: HttpRequest) -> JsonResponse:
    pending_user_id = request.session.get(TOTP_SESSION_KEY)
    if not pending_user_id:
        return JsonResponse({"detail": "TOTP challenge is not active"}, status=401)

    try:
        user = HumanUser.objects.select_related("employee_profile", "employee_profile__organization").get(
            id=pending_user_id
        )
    except HumanUser.DoesNotExist:
        request.session.pop(TOTP_SESSION_KEY, None)
        return JsonResponse({"detail": "TOTP challenge is not active"}, status=401)

    profile = user.employee_profile
    body = _json_body(request)
    if (
        not profile.totp_enabled
        or not profile.totp_secret
        or not _verify_totp(profile.totp_secret, str(body.get("code", "")))
    ):
        record_audit_event(
            action="identity.totp_verify_failed",
            actor=user,
            organization=profile.organization,
            result=AuditResult.DENIED,
            request=request,
        )
        return JsonResponse({"detail": "Invalid TOTP code"}, status=400)

    request.session.pop(TOTP_SESSION_KEY, None)
    login(request, user)
    record_audit_event(
        action="identity.login_succeeded",
        actor=user,
        organization=profile.organization,
        request=request,
    )
    return JsonResponse({"authenticated": True, "user": _user_payload(user)})
