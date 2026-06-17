import json

from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import AuditResult, HumanUser


def _json_body(request: HttpRequest) -> dict[str, object]:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def _user_payload(user: HumanUser) -> dict[str, object]:
    profile = user.employee_profile
    return {
        "email": user.email,
        "fullName": user.full_name,
        "role": profile.role,
        "organization": profile.organization.slug,
        "department": profile.department.code if profile.department else None,
        "mustChangePassword": profile.must_change_password,
        "totpRequired": profile.totp_required,
        "totpEnabled": profile.totp_enabled,
    }


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
    user = authenticate(request, username=email, password=password)
    if user is None:
        record_audit_event(action="identity.login_failed", result=AuditResult.DENIED, request=request)
        return JsonResponse({"detail": "Invalid credentials"}, status=401)
    if not hasattr(user, "employee_profile") or user.employee_profile.is_blocked:
        record_audit_event(action="identity.login_blocked", actor=user, result=AuditResult.DENIED, request=request)
        return JsonResponse({"detail": "Account is blocked"}, status=403)

    login(request, user)
    record_audit_event(
        action="identity.login_succeeded",
        actor=user,
        organization=user.employee_profile.organization,
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
    if not request.user.check_password(current_password):
        return JsonResponse({"detail": "Current password is invalid"}, status=400)
    if len(new_password) < 12:
        return JsonResponse({"detail": "Password is too short"}, status=400)

    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])
    profile = request.user.employee_profile
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
