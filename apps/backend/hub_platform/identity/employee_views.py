from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import IsManager
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.employee_support import employee_payload, get_owned_profile, temporary_password
from hub_platform.identity.governance import EmployeeAction, can_create_role, can_manage_employee
from hub_platform.identity.models import (
    POSITION_TITLE_MAX_LENGTH,
    AuditResult,
    Department,
    DepartmentStatus,
    EmployeeProfile,
    EmployeeRole,
    HumanUser,
)
from hub_platform.identity.sessions import revoke_user_sessions

# Роли, которые допустимо назначить через обычный employee flow (не OWNER —
# владелец появляется только через bootstrap или ownership transfer).
_ASSIGNABLE_ROLES = {EmployeeRole.ADMIN, EmployeeRole.EMPLOYEE}


def _clean_position_title(raw: object) -> tuple[str, str | None]:
    """Нормализует должность (SPEC-HUB-0016 §5). Возвращает (значение, ошибка)."""
    value = str(raw or "").strip()
    if not value:
        return "", "Position title is required"
    if len(value) > POSITION_TITLE_MAX_LENGTH:
        return value, f"Position title must be at most {POSITION_TITLE_MAX_LENGTH} characters"
    return value, None


def _resolve_department(organization, code: str) -> tuple[Department | None, str | None]:
    """Активный отдел организации по коду. Пустой код → company-level (None)."""
    code = (code or "").strip()
    if not code:
        return None, None
    try:
        department = Department.objects.get(
            organization=organization, code=code, status=DepartmentStatus.ACTIVE
        )
    except Department.DoesNotExist:
        return None, "Department not found"
    return department, None


def _deny(request: Request, target: EmployeeProfile | None, action: str) -> Response:
    """Отказ в privileged-действии с аудитом (SPEC-HUB-0016 §16)."""
    actor_profile = request.user.employee_profile
    record_audit_event(
        action="identity.employee_privileged_action_denied",
        actor=request.user,
        organization=actor_profile.organization,
        object_type="HumanUser",
        object_id=str(target.user_id) if target else "",
        result=AuditResult.DENIED,
        payload={"action": action, "targetRole": target.role if target else None},
        request=request,
    )
    return Response({"detail": "You cannot perform this action on this employee"}, status=403)


class EmployeeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        actor = request.user.employee_profile
        employees = EmployeeProfile.objects.select_related("user", "primary_department").filter(
            organization=actor.organization
        )
        # Compatibility (этап 1): обычный сотрудник видит только свой основной отдел.
        if actor.role == EmployeeRole.EMPLOYEE:
            employees = employees.filter(primary_department=actor.primary_department)
        return Response(
            {"items": [employee_payload(employee, actor) for employee in employees.order_by("user__email")]}
        )


class EmployeeCreateView(APIView):
    permission_classes = [IsManager]

    @transaction.atomic
    def post(self, request: Request) -> Response:
        actor = request.user.employee_profile
        body = request.data
        email = HumanUser.objects.normalize_email(str(body.get("email", "")))
        full_name = str(body.get("fullName", ""))
        provided_password = str(body.get("temporaryPassword", ""))
        position_title, position_error = _clean_position_title(body.get("positionTitle"))
        requested_role = str(body.get("role", EmployeeRole.EMPLOYEE))

        if not email:
            return Response({"detail": "Email is required"}, status=400)
        if requested_role not in _ASSIGNABLE_ROLES:
            return Response({"detail": "Invalid role"}, status=400)
        # Назначение ADMIN — только OWNER; ADMIN создаёт лишь EMPLOYEE (SPEC-HUB-0016 §8/§9).
        if not can_create_role(actor, requested_role):
            return _deny(request, None, f"{EmployeeAction.CREATE}:{requested_role}")
        if position_error:
            return Response({"detail": position_error}, status=400)
        if len(provided_password) < 12:
            return Response({"detail": "Temporary password must contain at least 12 characters"}, status=400)
        if HumanUser.objects.filter(email=email).exists():
            return Response({"detail": "Email is already used"}, status=400)

        # EMPLOYEE по умолчанию попадает в отдел продаж (compat этап 1); ADMIN — на уровень
        # компании, если отдел не задан. Отдел не выдаёт прав, только оргструктуру.
        department_code = str(body.get("department", "")).strip()
        if requested_role == EmployeeRole.EMPLOYEE and not department_code:
            department_code = "sales"
        department, department_error = _resolve_department(actor.organization, department_code)
        if department_error:
            return Response({"detail": department_error}, status=400)

        user = HumanUser.objects.create_user(
            email=email,
            password=provided_password,
            full_name=full_name,
            is_staff=False,
            is_superuser=False,
        )
        profile = EmployeeProfile.objects.create(
            user=user,
            organization=actor.organization,
            role=requested_role,
            position_title=position_title,
            primary_department=department,
            must_change_password=True,
        )
        record_audit_event(
            action="identity.employee_created",
            actor=request.user,
            organization=actor.organization,
            object_type="HumanUser",
            object_id=str(user.id),
            payload={"role": requested_role},
            request=request,
        )
        return Response({"employee": employee_payload(profile, actor)}, status=201)


class EmployeeUpdateView(APIView):
    permission_classes = [IsManager]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        # Базовое изменение данных — отдельная governance-группа (SPEC-HUB-0016 §10).
        if not can_manage_employee(actor, profile, EmployeeAction.UPDATE_PROFILE):
            return _deny(request, profile, EmployeeAction.UPDATE_PROFILE)

        body = request.data
        full_name = str(body.get("fullName", "")).strip()
        email = HumanUser.objects.normalize_email(str(body.get("email", "")).strip())
        phone = str(body.get("phone", "")).strip()
        position_title, position_error = _clean_position_title(body.get("positionTitle", profile.position_title))
        current_department_code = profile.primary_department.code if profile.primary_department else ""
        department_code = str(body.get("department", current_department_code))
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

        # Смена роли — отдельная группа, доступна только OWNER и только между
        # ADMIN/EMPLOYEE (владелец — через ownership transfer).
        role_changing = requested_role != profile.role
        if role_changing:
            if requested_role not in _ASSIGNABLE_ROLES:
                return Response({"detail": "Invalid role"}, status=400)
            if not can_manage_employee(actor, profile, EmployeeAction.CHANGE_ROLE):
                return _deny(request, profile, EmployeeAction.CHANGE_ROLE)

        department, department_error = _resolve_department(profile.organization, department_code)
        if department_error:
            return Response({"detail": department_error}, status=400)
        placement_changing = (department.id if department else None) != profile.primary_department_id
        if placement_changing and not can_manage_employee(actor, profile, EmployeeAction.CHANGE_PLACEMENT):
            return _deny(request, profile, EmployeeAction.CHANGE_PLACEMENT)

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
            update_fields=["phone", "position_title", "role", "primary_department", "totp_enabled", "totp_secret"]
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


class EmployeeResetPasswordView(APIView):
    permission_classes = [IsManager]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        if not can_manage_employee(actor, profile, EmployeeAction.RESET_PASSWORD):
            return _deny(request, profile, EmployeeAction.RESET_PASSWORD)
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
        return Response({"employee": employee_payload(profile, actor), "temporaryPassword": password})


class EmployeeRevokeSessionsView(APIView):
    permission_classes = [IsManager]

    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        if not can_manage_employee(actor, profile, EmployeeAction.TERMINATE_SESSIONS):
            return _deny(request, profile, EmployeeAction.TERMINATE_SESSIONS)
        revoked = revoke_user_sessions(profile.user_id)
        record_audit_event(
            action="identity.employee_sessions_terminated",
            actor=request.user,
            organization=profile.organization,
            object_type="HumanUser",
            object_id=str(profile.user_id),
            payload={"revoked": revoked},
            request=request,
        )
        return Response({"employee": employee_payload(profile, actor), "revoked": revoked})


class EmployeeBlockView(APIView):
    permission_classes = [IsManager]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        if not can_manage_employee(actor, profile, EmployeeAction.BLOCK):
            return _deny(request, profile, EmployeeAction.BLOCK)
        profile.block()
        revoke_user_sessions(profile.user_id)
        record_audit_event(
            action="identity.employee_blocked",
            actor=request.user,
            organization=profile.organization,
            object_type="HumanUser",
            object_id=str(profile.user_id),
            request=request,
        )
        return Response({"employee": employee_payload(profile, actor)})


class EmployeeUnblockView(APIView):
    permission_classes = [IsManager]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        if not can_manage_employee(actor, profile, EmployeeAction.UNBLOCK):
            return _deny(request, profile, EmployeeAction.UNBLOCK)
        profile.blocked_at = None
        profile.user.is_active = True
        profile.user.save(update_fields=["is_active"])
        profile.save(update_fields=["blocked_at"])
        record_audit_event(
            action="identity.employee_unblocked",
            actor=request.user,
            organization=profile.organization,
            object_type="HumanUser",
            object_id=str(profile.user_id),
            request=request,
        )
        return Response({"employee": employee_payload(profile, actor)})


class OwnershipTransferView(APIView):
    """Атомарная передача владения (ADR-HUB-0027, SPEC-HUB-0016 §12).

    Инициатор — действующий OWNER; target становится OWNER и переводится на уровень
    компании; прежний владелец получает явно выбранную роль ADMIN или EMPLOYEE.
    Промежуточное состояние без владельца или с двумя владельцами невозможно —
    прежний владелец понижается до промоута target (инвариант ровно одного OWNER)."""

    permission_classes = [IsManager]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        # Блокируем обе записи, чтобы конкурентная передача не создала двух владельцев.
        # of=("self",): FOR UPDATE только по строкам EmployeeProfile — nullable
        # primary_department даёт LEFT JOIN, который Postgres не разрешает лочить.
        actor = (
            EmployeeProfile.objects.select_for_update(of=("self",))
            .select_related("user", "primary_department")
            .get(pk=request.user.employee_profile.pk)
        )
        try:
            target = (
                EmployeeProfile.objects.select_for_update(of=("self",))
                .select_related("user", "primary_department")
                .get(user_id=user_id, organization=actor.organization)
            )
        except EmployeeProfile.DoesNotExist:
            return Response({"detail": "Employee not found"}, status=404)

        if not can_manage_employee(actor, target, EmployeeAction.TRANSFER_OWNERSHIP):
            return _deny(request, target, EmployeeAction.TRANSFER_OWNERSHIP)
        if target.is_blocked or not target.user.is_active:
            return Response({"detail": "Target must be an active employee"}, status=409)

        previous_owner_role = str(request.data.get("previousOwnerRole", EmployeeRole.ADMIN))
        if previous_owner_role not in _ASSIGNABLE_ROLES:
            return Response({"detail": "Previous owner role must be ADMIN or EMPLOYEE"}, status=400)

        previous_department = None
        if previous_owner_role == EmployeeRole.EMPLOYEE:
            previous_department, department_error = _resolve_department(
                actor.organization, str(request.data.get("previousOwnerDepartment", ""))
            )
            if department_error:
                return Response({"detail": department_error}, status=400)

        # Понижаем прежнего владельца ПЕРЕД промоутом target — иначе partial unique
        # constraint (ровно один OWNER на организацию) отклонит второго владельца.
        actor.role = previous_owner_role
        actor.primary_department = previous_department
        actor.save(update_fields=["role", "primary_department"])

        target.role = EmployeeRole.OWNER
        target.primary_department = None
        target.save(update_fields=["role", "primary_department"])

        record_audit_event(
            action="identity.ownership_transferred",
            actor=request.user,
            organization=actor.organization,
            object_type="HumanUser",
            object_id=str(target.user_id),
            payload={
                "from": actor.user_id,
                "to": target.user_id,
                "previousOwnerRole": previous_owner_role,
            },
            request=request,
        )
        return Response(
            {
                "employee": employee_payload(target, actor),
                "previousOwner": employee_payload(actor, actor),
            }
        )
