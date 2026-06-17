import base64
import hashlib
import hmac
import json
import os
import struct
import time
from urllib.parse import quote

from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, JsonResponse
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
