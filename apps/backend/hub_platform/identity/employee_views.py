from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.events.services import DomainEvent, enqueue_event
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.access_services import create_access_assignment
from hub_platform.identity.employee_support import employee_payload, get_owned_profile
from hub_platform.identity.employee_validation import (
    ASSIGNABLE_ROLES,
    clean_position_title,
    deny_employee_action,
    resolve_department,
)
from hub_platform.identity.event_handlers import INITIAL_ACCESS_REQUESTED
from hub_platform.identity.governance import EmployeeAction, can_create_role, can_manage_employee
from hub_platform.identity.models import EmployeeProfile, EmployeeRole, HumanUser
from hub_platform.identity.policy import (
    ResourceScope,
    accessible_department_ids,
    authorize,
    has_capability_any_scope,
)
from hub_platform.identity.sessions import revoke_user_sessions


class EmployeeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        actor = request.user.employee_profile
        if not has_capability_any_scope(request.user, "employees.view"):
            return Response({"detail": "Not allowed"}, status=403)
        employees = (
            EmployeeProfile.objects.select_related("user", "primary_department")
            .prefetch_related("access_assignments__access_profile__capability_links")
            .filter(organization=actor.organization)
        )
        department_ids = accessible_department_ids(request.user, "employees.view")
        if department_ids is not None:
            employees = employees.filter(primary_department_id__in=department_ids)
        return Response(
            {
                "items": [
                    employee_payload(employee, actor)
                    for employee in employees.order_by("user__email")
                ]
            }
        )


class EmployeeCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request) -> Response:
        actor = request.user.employee_profile
        body = request.data
        email = HumanUser.objects.normalize_email(str(body.get("email", "")))
        full_name = str(body.get("fullName", "")).strip()
        phone = str(body.get("phone", "")).strip()
        provided_password = str(body.get("temporaryPassword", ""))
        position_title, position_error = clean_position_title(body.get("positionTitle"))
        requested_role = str(body.get("role", EmployeeRole.EMPLOYEE))
        assignments = body.get("accessAssignments", [])

        if requested_role not in ASSIGNABLE_ROLES:
            return Response({"detail": "Invalid role"}, status=400)
        if not can_create_role(actor, requested_role):
            return deny_employee_action(
                request, None, f"{EmployeeAction.CREATE}:{requested_role}"
            )
        if not email:
            return Response({"detail": "Email is required"}, status=400)
        if not full_name:
            return Response({"detail": "Full name is required"}, status=400)
        if not isinstance(assignments, list) or any(
            not isinstance(assignment, dict) for assignment in assignments
        ):
            return Response({"detail": "accessAssignments must be a list"}, status=400)
        if requested_role == EmployeeRole.ADMIN and assignments:
            return Response({"detail": "ADMIN access is defined by the system role"}, status=400)
        if position_error:
            return Response({"detail": position_error}, status=400)
        if provided_password and len(provided_password) < 12:
            return Response(
                {"detail": "Temporary password must contain at least 12 characters"},
                status=400,
            )
        if HumanUser.objects.filter(email=email).exists():
            return Response({"detail": "Email is already used"}, status=400)

        department, department_error = resolve_department(
            actor.organization, str(body.get("department", "")).strip()
        )
        if department_error:
            return Response({"detail": department_error}, status=400)

        user = HumanUser.objects.create_user(
            email=email,
            password=provided_password or None,
            full_name=full_name,
            is_staff=False,
            is_superuser=False,
        )
        profile = EmployeeProfile.objects.create(
            user=user,
            organization=actor.organization,
            role=requested_role,
            position_title=position_title,
            phone=phone,
            primary_department=department,
            must_change_password=True,
        )
        try:
            for assignment in assignments:
                create_access_assignment(actor=actor, employee=profile, payload=assignment)
        except (ValidationError, IntegrityError) as error:
            transaction.set_rollback(True)
            return Response({"detail": str(error)}, status=400)
        record_audit_event(
            action="identity.employee_created",
            actor=request.user,
            organization=actor.organization,
            object_type="HumanUser",
            object_id=str(user.id),
            payload={"role": requested_role},
            request=request,
        )
        if not provided_password:
            enqueue_event(
                DomainEvent(
                    aggregate_type="HumanUser",
                    aggregate_id=str(user.id),
                    event_type=INITIAL_ACCESS_REQUESTED,
                    payload={"userId": user.id},
                )
            )
        return Response({"employee": employee_payload(profile, actor)}, status=201)


class EmployeeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        scope = ResourceScope(profile.organization_id, profile.primary_department_id)
        if not authorize(request.user, "employees.view", scope):
            return Response({"detail": "Employee not found"}, status=404)
        return Response({"employee": employee_payload(profile, actor, include_detail=True)})


class EmployeeUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        if not can_manage_employee(actor, profile, EmployeeAction.UPDATE_PROFILE):
            return deny_employee_action(request, profile, EmployeeAction.UPDATE_PROFILE)

        body = request.data
        full_name = str(body.get("fullName", "")).strip()
        email = HumanUser.objects.normalize_email(str(body.get("email", "")).strip())
        phone = str(body.get("phone", "")).strip()
        position_title, position_error = clean_position_title(
            body.get("positionTitle", profile.position_title)
        )
        current_department_code = (
            profile.primary_department.code if profile.primary_department else ""
        )
        requested_role = str(body.get("role", profile.role))
        totp_enabled = body.get("totpEnabled", profile.totp_enabled)

        if not full_name:
            return Response({"detail": "Full name is required"}, status=400)
        if not email:
            return Response({"detail": "Email is required"}, status=400)
        if HumanUser.objects.exclude(id=profile.user_id).filter(email=email).exists():
            return Response({"detail": "Email is already used"}, status=400)
        if position_error:
            return Response({"detail": position_error}, status=400)

        role_changing = requested_role != profile.role
        if role_changing:
            if requested_role not in ASSIGNABLE_ROLES:
                return Response({"detail": "Invalid role"}, status=400)
            if not can_manage_employee(actor, profile, EmployeeAction.CHANGE_ROLE):
                return deny_employee_action(request, profile, EmployeeAction.CHANGE_ROLE)

        department, department_error = resolve_department(
            profile.organization, str(body.get("department", current_department_code))
        )
        if department_error:
            return Response({"detail": department_error}, status=400)
        placement_changing = (
            department.id if department else None
        ) != profile.primary_department_id
        if placement_changing and not can_manage_employee(
            actor, profile, EmployeeAction.CHANGE_PLACEMENT
        ):
            return deny_employee_action(request, profile, EmployeeAction.CHANGE_PLACEMENT)

        profile.user.full_name = full_name
        profile.user.email = email
        profile.user.save(update_fields=["full_name", "email"])
        profile.phone = phone
        profile.position_title = position_title
        profile.role = requested_role
        profile.primary_department = department
        profile.totp_enabled = bool(totp_enabled)
        if not profile.totp_enabled:
            profile.totp_secret = ""
        profile.save(
            update_fields=[
                "phone",
                "position_title",
                "role",
                "primary_department",
                "totp_enabled",
                "totp_secret",
            ]
        )

        record_audit_event(
            action="identity.employee_updated",
            actor=request.user,
            organization=profile.organization,
            object_type="HumanUser",
            object_id=str(profile.user_id),
            request=request,
        )
        if role_changing:
            record_audit_event(
                action="identity.employee_role_changed",
                actor=request.user,
                organization=profile.organization,
                object_type="HumanUser",
                object_id=str(profile.user_id),
                payload={"role": profile.role},
                request=request,
            )
            revoke_user_sessions(profile.user_id)
        if placement_changing:
            record_audit_event(
                action="identity.employee_placement_changed",
                actor=request.user,
                organization=profile.organization,
                object_type="HumanUser",
                object_id=str(profile.user_id),
                payload={"department": department.code if department else None},
                request=request,
            )
        return Response({"employee": employee_payload(profile, actor)})
