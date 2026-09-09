from django.db import transaction
from django.http import FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.pagination import page_payload, paginate
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.identity.audit import record_audit_event
from chatballs.identity.employee_password import clean_password_mode, issue_initial_password
from chatballs.identity.employee_selectors import employees_for
from chatballs.identity.employee_support import employee_payload, get_owned_profile
from chatballs.identity.employee_validation import (
    ASSIGNABLE_ROLES,
    clean_position_title,
    deny_employee_action,
    resolve_groups,
)
from chatballs.identity.event_handlers import INITIAL_ACCESS_REQUESTED
from chatballs.identity.governance import EmployeeAction, can_create_role, can_manage_employee
from chatballs.identity.group_models import EmployeeGroupMember
from chatballs.identity.models import EmployeeRole, HumanUser, OrganizationMembership
from chatballs.identity.policy import has_capability_any_scope


def _set_groups(profile: OrganizationMembership, groups) -> None:
    profile.group_links.all().delete()
    EmployeeGroupMember.objects.bulk_create(
        [
            EmployeeGroupMember(
                organization_id=profile.organization_id,
                group=group,
                employee=profile,
            )
            for group in groups
        ]
    )


class EmployeeAvatarView(APIView):
    """Фото коллеги — любому участнику организации (сайдбар, подписи, выбор ответственного)."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, user_id: int) -> Response | FileResponse:
        membership = (
            OrganizationMembership.objects.select_related("user")
            .filter(organization=request.tenant_context.organization, user_id=user_id)
            .first()
        )
        if membership is None or not membership.user.avatar:
            return Response({"detail": "Фото не найдено"}, status=404)
        response = FileResponse(
            membership.user.avatar.open("rb"),
            content_type=membership.user.avatar_content_type or "application/octet-stream",
            filename="avatar",
        )
        response["Cache-Control"] = "private, max-age=86400"
        return response


class EmployeeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        actor = request.tenant_context.membership
        if not has_capability_any_scope(actor, "employees.view"):
            return Response({"detail": "Not allowed"}, status=403)
        page = paginate(
            employees_for(actor.organization_id, request.query_params),
            request.query_params,
        )
        return Response(page_payload(page, lambda employee: employee_payload(employee, actor)))


class EmployeeCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request) -> Response:
        actor = request.tenant_context.membership
        body = request.data
        email = HumanUser.objects.normalize_email(str(body.get("email", "")))
        full_name = str(body.get("fullName", "")).strip()
        phone = str(body.get("phone", "")).strip()
        provided_password = str(body.get("temporaryPassword", ""))
        # Кадры E5/E6: пароль первичного доступа письмом либо показать один раз.
        password_mode = clean_password_mode(body.get("passwordMode"))
        position_title, position_error = clean_position_title(body.get("positionTitle"))
        requested_role = str(body.get("role", EmployeeRole.EMPLOYEE))

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
        if position_error:
            return Response({"detail": position_error}, status=400)
        if provided_password:
            return Response({"detail": "Temporary passwords are not supported"}, status=400)
        if password_mode is None:
            return Response({"detail": "Unknown password mode"}, status=400)
        if HumanUser.objects.filter(email=email).exists():
            return Response({"detail": "Email is already used"}, status=400)

        groups, groups_error = resolve_groups(actor.organization, body.get("groupIds"))
        if groups_error:
            return Response({"detail": groups_error}, status=400)

        user = HumanUser.objects.create_user(
            email=email,
            password=None,
            full_name=full_name,
            is_staff=False,
            is_superuser=False,
            must_change_password=True,
        )
        profile = OrganizationMembership.objects.create(
            user=user,
            organization=actor.organization,
            role=requested_role,
            position_title=position_title,
            phone=phone,
        )
        if groups:
            _set_groups(profile, groups)
        password = issue_initial_password(user) if password_mode == "show" else None
        record_audit_event(
            action="identity.employee_created",
            actor=request.user,
            organization=actor.organization,
            object_type="HumanUser",
            object_id=str(user.id),
            payload={"role": requested_role, "passwordMode": password_mode},
            request=request,
        )
        if password_mode == "mail":
            enqueue_event(
                DomainEvent(
                    aggregate_type="HumanUser",
                    aggregate_id=str(user.id),
                    event_type=INITIAL_ACCESS_REQUESTED,
                    payload={"userId": user.id},
                    tenant_context=request.tenant_context,
                )
            )
        return Response(
            {"employee": employee_payload(profile, actor), "password": password},
            status=201,
        )


class EmployeeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, user_id: int) -> Response:
        actor = request.tenant_context.membership
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        if not has_capability_any_scope(actor, "employees.view"):
            return Response({"detail": "Employee not found"}, status=404)
        return Response({"employee": employee_payload(profile, actor, include_detail=True)})


class EmployeeUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.tenant_context.membership
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
        requested_role = str(body.get("role", profile.role))

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

        groups, groups_error = resolve_groups(profile.organization, body.get("groupIds"))
        if groups_error:
            return Response({"detail": groups_error}, status=400)
        if groups is not None and not can_manage_employee(
            actor, profile, EmployeeAction.CHANGE_GROUPS
        ):
            return deny_employee_action(request, profile, EmployeeAction.CHANGE_GROUPS)

        profile.user.full_name = full_name
        profile.user.email = email
        profile.user.save(update_fields=["full_name", "email"])
        profile.phone = phone
        profile.position_title = position_title
        profile.role = requested_role
        profile.save(update_fields=["phone", "position_title", "role"])
        if groups is not None:
            _set_groups(profile, groups)

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
        if groups is not None:
            record_audit_event(
                action="identity.employee_groups_changed",
                actor=request.user,
                organization=profile.organization,
                object_type="HumanUser",
                object_id=str(profile.user_id),
                payload={"groupIds": [group.id for group in groups]},
                request=request,
            )
        return Response({"employee": employee_payload(profile, actor)})
