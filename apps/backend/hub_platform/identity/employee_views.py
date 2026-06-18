import json
import secrets
import string
from functools import wraps
from typing import Callable

from django.db import transaction
from django.contrib.sessions.models import Session
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import AuditResult, Department, EmployeeProfile, EmployeeRole, HumanUser
from hub_platform.identity.permissions import is_owner


def _json_body(request: HttpRequest) -> dict[str, object]:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def owner_required(view_func: Callable[[HttpRequest, object], JsonResponse]):
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> JsonResponse:
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Authentication required"}, status=401)
        if not is_owner(request.user):
            organization = getattr(getattr(request.user, "employee_profile", None), "organization", None)
            record_audit_event(
                action="identity.owner_permission_denied",
                actor=request.user,
                organization=organization,
                result=AuditResult.DENIED,
                request=request,
            )
            return JsonResponse({"detail": "Owner role required"}, status=403)
        return view_func(request, *args, **kwargs)

    return wrapper


def _employee_payload(profile: EmployeeProfile) -> dict[str, object]:
    return {
        "id": profile.user_id,
        "email": profile.user.email,
        "fullName": profile.user.full_name,
        "role": profile.role,
        "phone": profile.phone,
        "department": profile.department.code if profile.department else None,
        "isActive": profile.user.is_active,
        "isBlocked": profile.is_blocked,
        "mustChangePassword": profile.must_change_password,
        "totpRequired": profile.totp_required,
        "totpEnabled": profile.totp_enabled,
    }


@require_GET
def employee_list_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)
    profile = request.user.employee_profile
    employees = EmployeeProfile.objects.select_related("user", "department").filter(
        organization=profile.organization
    )
    if profile.role == EmployeeRole.OPERATOR:
        employees = employees.filter(department=profile.department)
    return JsonResponse({"items": [_employee_payload(employee) for employee in employees.order_by("user__email")]})


@csrf_protect
@require_POST
@owner_required
@transaction.atomic
def create_operator_view(request: HttpRequest) -> JsonResponse:
    owner_profile = request.user.employee_profile
    body = _json_body(request)
    email = HumanUser.objects.normalize_email(str(body.get("email", "")))
    full_name = str(body.get("fullName", ""))
    temporary_password = str(body.get("temporaryPassword", ""))
    if not email:
        return JsonResponse({"detail": "Email is required"}, status=400)
    if len(temporary_password) < 12:
        return JsonResponse({"detail": "Temporary password must contain at least 12 characters"}, status=400)

    sales_department = Department.objects.get(organization=owner_profile.organization, code="sales")
    user = HumanUser.objects.create_user(
        email=email,
        password=temporary_password,
        full_name=full_name,
        is_staff=False,
        is_superuser=False,
    )
    profile = EmployeeProfile.objects.create(
        user=user,
        organization=owner_profile.organization,
        role=EmployeeRole.OPERATOR,
        department=sales_department,
        must_change_password=True,
    )
    record_audit_event(
        action="identity.operator_created",
        actor=request.user,
        organization=owner_profile.organization,
        object_type="HumanUser",
        object_id=str(user.id),
        request=request,
    )
    return JsonResponse({"employee": _employee_payload(profile)}, status=201)


def _get_owned_profile(request: HttpRequest, user_id: int) -> EmployeeProfile | None:
    owner_profile = request.user.employee_profile
    try:
        return EmployeeProfile.objects.select_related("user", "department").get(
            user_id=user_id,
            organization=owner_profile.organization,
        )
    except EmployeeProfile.DoesNotExist:
        return None


def _temporary_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Temp-" + "".join(secrets.choice(alphabet) for _ in range(14)) + "!"


def _revoke_user_sessions(user_id: int) -> int:
    revoked = 0
    for session in Session.objects.all():
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == str(user_id):
            session.delete()
            revoked += 1
    return revoked


@csrf_protect
@require_POST
@owner_required
@transaction.atomic
def update_employee_view(request: HttpRequest, user_id: int) -> JsonResponse:
    profile = _get_owned_profile(request, user_id)
    if profile is None:
        return JsonResponse({"detail": "Employee not found"}, status=404)

    body = _json_body(request)
    full_name = str(body.get("fullName", "")).strip()
    email = HumanUser.objects.normalize_email(str(body.get("email", "")).strip())
    phone = str(body.get("phone", "")).strip()
    role = str(body.get("role", profile.role))
    department_code = str(body.get("department", profile.department.code if profile.department else ""))
    totp_enabled = body.get("totpEnabled", profile.totp_enabled)

    if not full_name:
        return JsonResponse({"detail": "Full name is required"}, status=400)
    if not email:
        return JsonResponse({"detail": "Email is required"}, status=400)
    if HumanUser.objects.exclude(id=profile.user_id).filter(email=email).exists():
        return JsonResponse({"detail": "Email is already used"}, status=400)
    if role not in EmployeeRole.values:
        return JsonResponse({"detail": "Invalid role"}, status=400)

    department = None
    if department_code:
        try:
            department = Department.objects.get(organization=profile.organization, code=department_code)
        except Department.DoesNotExist:
            return JsonResponse({"detail": "Department not found"}, status=400)

    profile.user.full_name = full_name
    profile.user.email = email
    profile.user.save(update_fields=["full_name", "email"])
    profile.phone = phone
    profile.role = role
    profile.department = department
    profile.totp_enabled = bool(totp_enabled)
    if not profile.totp_enabled:
        profile.totp_secret = ""
    profile.save(update_fields=["phone", "role", "department", "totp_enabled", "totp_secret"])

    record_audit_event(
        action="identity.employee_updated",
        actor=request.user,
        organization=profile.organization,
        object_type="HumanUser",
        object_id=str(profile.user_id),
        request=request,
    )
    return JsonResponse({"employee": _employee_payload(profile)})


@csrf_protect
@require_POST
@owner_required
@transaction.atomic
def reset_employee_password_view(request: HttpRequest, user_id: int) -> JsonResponse:
    profile = _get_owned_profile(request, user_id)
    if profile is None:
        return JsonResponse({"detail": "Employee not found"}, status=404)
    temporary_password = _temporary_password()
    profile.user.set_password(temporary_password)
    profile.user.save(update_fields=["password"])
    profile.must_change_password = True
    profile.save(update_fields=["must_change_password"])
    _revoke_user_sessions(profile.user_id)
    record_audit_event(
        action="identity.employee_password_reset",
        actor=request.user,
        organization=profile.organization,
        object_type="HumanUser",
        object_id=str(profile.user_id),
        request=request,
    )
    return JsonResponse({"employee": _employee_payload(profile), "temporaryPassword": temporary_password})


@csrf_protect
@require_POST
@owner_required
def revoke_employee_sessions_view(request: HttpRequest, user_id: int) -> JsonResponse:
    profile = _get_owned_profile(request, user_id)
    if profile is None:
        return JsonResponse({"detail": "Employee not found"}, status=404)
    revoked = _revoke_user_sessions(profile.user_id)
    record_audit_event(
        action="identity.employee_sessions_revoked",
        actor=request.user,
        organization=profile.organization,
        object_type="HumanUser",
        object_id=str(profile.user_id),
        payload={"revoked": revoked},
        request=request,
    )
    return JsonResponse({"employee": _employee_payload(profile), "revoked": revoked})


@csrf_protect
@require_POST
@owner_required
@transaction.atomic
def block_employee_view(request: HttpRequest, user_id: int) -> JsonResponse:
    profile = _get_owned_profile(request, user_id)
    if profile is None:
        return JsonResponse({"detail": "Employee not found"}, status=404)

    if profile.role == EmployeeRole.OWNER:
        return JsonResponse({"detail": "Owner cannot be blocked by this operation"}, status=400)
    profile.block()
    _revoke_user_sessions(profile.user_id)
    record_audit_event(
        action="identity.operator_blocked",
        actor=request.user,
        organization=profile.organization,
        object_type="HumanUser",
        object_id=str(profile.user_id),
        request=request,
    )
    return JsonResponse({"employee": _employee_payload(profile)})


@csrf_protect
@require_POST
@owner_required
@transaction.atomic
def unblock_employee_view(request: HttpRequest, user_id: int) -> JsonResponse:
    profile = _get_owned_profile(request, user_id)
    if profile is None:
        return JsonResponse({"detail": "Employee not found"}, status=404)
    profile.blocked_at = None
    profile.user.is_active = True
    profile.user.save(update_fields=["is_active"])
    profile.save(update_fields=["blocked_at"])
    record_audit_event(
        action="identity.operator_unblocked",
        actor=request.user,
        organization=profile.organization,
        object_type="HumanUser",
        object_id=str(profile.user_id),
        request=request,
    )
    return JsonResponse({"employee": _employee_payload(profile)})
