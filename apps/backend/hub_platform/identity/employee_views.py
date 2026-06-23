from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import IsOwner
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.employee_support import employee_payload, get_owned_profile, temporary_password
from hub_platform.identity.models import Department, EmployeeProfile, EmployeeRole, HumanUser
from hub_platform.identity.sessions import revoke_user_sessions


class EmployeeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        profile = request.user.employee_profile
        employees = EmployeeProfile.objects.select_related("user", "department").filter(
            organization=profile.organization
        )
        if profile.role == EmployeeRole.OPERATOR:
            employees = employees.filter(department=profile.department)
        return Response({"items": [employee_payload(employee) for employee in employees.order_by("user__email")]})


class OperatorCreateView(APIView):
    permission_classes = [IsOwner]

    @transaction.atomic
    def post(self, request: Request) -> Response:
        owner_profile = request.user.employee_profile
        body = request.data
        email = HumanUser.objects.normalize_email(str(body.get("email", "")))
        full_name = str(body.get("fullName", ""))
        provided_password = str(body.get("temporaryPassword", ""))
        if not email:
            return Response({"detail": "Email is required"}, status=400)
        if len(provided_password) < 12:
            return Response({"detail": "Temporary password must contain at least 12 characters"}, status=400)

        sales_department = Department.objects.get(organization=owner_profile.organization, code="sales")
        user = HumanUser.objects.create_user(
            email=email,
            password=provided_password,
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
        return Response({"employee": employee_payload(profile)}, status=201)


class EmployeeUpdateView(APIView):
    permission_classes = [IsOwner]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)

        body = request.data
        full_name = str(body.get("fullName", "")).strip()
        email = HumanUser.objects.normalize_email(str(body.get("email", "")).strip())
        phone = str(body.get("phone", "")).strip()
        role = str(body.get("role", profile.role))
        department_code = str(body.get("department", profile.department.code if profile.department else ""))
        totp_enabled = body.get("totpEnabled", profile.totp_enabled)

        if not full_name:
            return Response({"detail": "Full name is required"}, status=400)
        if not email:
            return Response({"detail": "Email is required"}, status=400)
        if HumanUser.objects.exclude(id=profile.user_id).filter(email=email).exists():
            return Response({"detail": "Email is already used"}, status=400)
        if role not in EmployeeRole.values:
            return Response({"detail": "Invalid role"}, status=400)

        department = None
        if department_code:
            try:
                department = Department.objects.get(organization=profile.organization, code=department_code)
            except Department.DoesNotExist:
                return Response({"detail": "Department not found"}, status=400)

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
        return Response({"employee": employee_payload(profile)})


class EmployeeResetPasswordView(APIView):
    permission_classes = [IsOwner]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        password = temporary_password()
        profile.user.set_password(password)
        profile.user.save(update_fields=["password"])
        profile.must_change_password = True
        profile.save(update_fields=["must_change_password"])
        revoke_user_sessions(profile.user_id)
        record_audit_event(
            action="identity.employee_password_reset",
            actor=request.user,
            organization=profile.organization,
            object_type="HumanUser",
            object_id=str(profile.user_id),
            request=request,
        )
        return Response({"employee": employee_payload(profile), "temporaryPassword": password})


class EmployeeRevokeSessionsView(APIView):
    permission_classes = [IsOwner]

    def post(self, request: Request, user_id: int) -> Response:
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        revoked = revoke_user_sessions(profile.user_id)
        record_audit_event(
            action="identity.employee_sessions_revoked",
            actor=request.user,
            organization=profile.organization,
            object_type="HumanUser",
            object_id=str(profile.user_id),
            payload={"revoked": revoked},
            request=request,
        )
        return Response({"employee": employee_payload(profile), "revoked": revoked})


class EmployeeBlockView(APIView):
    permission_classes = [IsOwner]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        if profile.role == EmployeeRole.OWNER:
            return Response({"detail": "Owner cannot be blocked by this operation"}, status=400)
        profile.block()
        revoke_user_sessions(profile.user_id)
        record_audit_event(
            action="identity.operator_blocked",
            actor=request.user,
            organization=profile.organization,
            object_type="HumanUser",
            object_id=str(profile.user_id),
            request=request,
        )
        return Response({"employee": employee_payload(profile)})


class EmployeeUnblockView(APIView):
    permission_classes = [IsOwner]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
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
        return Response({"employee": employee_payload(profile)})
