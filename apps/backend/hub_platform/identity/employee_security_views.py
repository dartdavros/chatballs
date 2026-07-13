from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.employee_support import employee_payload, get_owned_profile, temporary_password
from hub_platform.identity.employee_validation import deny_employee_action
from hub_platform.identity.governance import EmployeeAction, can_manage_employee
from hub_platform.identity.sessions import revoke_user_sessions


class EmployeeResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        if not can_manage_employee(actor, profile, EmployeeAction.RESET_PASSWORD):
            return deny_employee_action(request, profile, EmployeeAction.RESET_PASSWORD)
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
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        if not can_manage_employee(actor, profile, EmployeeAction.TERMINATE_SESSIONS):
            return deny_employee_action(request, profile, EmployeeAction.TERMINATE_SESSIONS)
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
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": "Employee not found"}, status=404)
        if not can_manage_employee(actor, profile, EmployeeAction.UNBLOCK):
            return deny_employee_action(request, profile, EmployeeAction.UNBLOCK)
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

