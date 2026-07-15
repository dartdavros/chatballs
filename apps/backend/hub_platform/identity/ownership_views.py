from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.employee_support import employee_payload
from hub_platform.identity.employee_validation import (
    ASSIGNABLE_ROLES,
    deny_employee_action,
    resolve_department,
)
from hub_platform.identity.governance import EmployeeAction, can_manage_employee
from hub_platform.identity.models import EmployeeRole, OrganizationMembership


class OwnershipTransferView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = (
            OrganizationMembership.objects.select_for_update(of=("self",))
            .select_related("user", "primary_department")
            .get(pk=request.tenant_context.membership.pk)
        )
        try:
            target = (
                OrganizationMembership.objects.select_for_update(of=("self",))
                .select_related("user", "primary_department")
                .get(user_id=user_id, organization=actor.organization)
            )
        except OrganizationMembership.DoesNotExist:
            return Response({"detail": "Employee not found"}, status=404)

        if not can_manage_employee(actor, target, EmployeeAction.TRANSFER_OWNERSHIP):
            return deny_employee_action(request, target, EmployeeAction.TRANSFER_OWNERSHIP)
        if target.is_blocked or not target.user.is_active:
            return Response({"detail": "Target must be an active employee"}, status=409)

        previous_owner_role = str(request.data.get("previousOwnerRole", EmployeeRole.ADMIN))
        if previous_owner_role not in ASSIGNABLE_ROLES:
            return Response({"detail": "Previous owner role must be ADMIN or EMPLOYEE"}, status=400)

        previous_department = None
        if previous_owner_role == EmployeeRole.EMPLOYEE:
            previous_department, department_error = resolve_department(
                actor.organization, str(request.data.get("previousOwnerDepartment", ""))
            )
            if department_error:
                return Response({"detail": department_error}, status=400)

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
