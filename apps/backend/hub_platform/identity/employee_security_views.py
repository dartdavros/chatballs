from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.employee_support import employee_payload, get_owned_profile
from hub_platform.identity.employee_validation import deny_employee_action
from hub_platform.identity.governance import EmployeeAction, can_manage_employee


class EmployeeResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        return deny_employee_action(request, profile, EmployeeAction.RESET_PASSWORD)


class EmployeeRevokeSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        return deny_employee_action(request, profile, EmployeeAction.TERMINATE_SESSIONS)


class EmployeeBlockView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        if not can_manage_employee(actor, profile, EmployeeAction.BLOCK):
            return deny_employee_action(request, profile, EmployeeAction.BLOCK)
        profile.block()
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
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        if not can_manage_employee(actor, profile, EmployeeAction.UNBLOCK):
            return deny_employee_action(request, profile, EmployeeAction.UNBLOCK)
        profile.unblock()
        record_audit_event(
            action="identity.employee_unblocked",
            actor=request.user,
            organization=profile.organization,
            object_type="HumanUser",
            object_id=str(profile.user_id),
            request=request,
        )
        return Response({"employee": employee_payload(profile, actor)})
