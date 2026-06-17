import json
from functools import wraps
from typing import Callable

from django.db import transaction
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


@csrf_protect
@require_POST
@owner_required
@transaction.atomic
def block_employee_view(request: HttpRequest, user_id: int) -> JsonResponse:
    owner_profile = request.user.employee_profile
    try:
        profile = EmployeeProfile.objects.select_related("user").get(
            user_id=user_id,
            organization=owner_profile.organization,
        )
    except EmployeeProfile.DoesNotExist:
        return JsonResponse({"detail": "Employee not found"}, status=404)

    if profile.role == EmployeeRole.OWNER:
        return JsonResponse({"detail": "Owner cannot be blocked by this operation"}, status=400)
    profile.block()
    record_audit_event(
        action="identity.operator_blocked",
        actor=request.user,
        organization=owner_profile.organization,
        object_type="HumanUser",
        object_id=str(profile.user_id),
        request=request,
    )
    return JsonResponse({"employee": _employee_payload(profile)})
