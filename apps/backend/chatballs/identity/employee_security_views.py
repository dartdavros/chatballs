from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.employee_password import clean_password_mode, reset_employee_password
from chatballs.identity.employee_support import employee_payload, get_owned_profile
from chatballs.identity.employee_validation import deny_employee_action
from chatballs.identity.governance import EmployeeAction, can_manage_employee
from chatballs.identity.sessions import revoke_user_sessions


class EmployeeResetPasswordView(APIView):
    """Сброс пароля сотрудника (дизайн-базлайн v2, кадр E8).

    ``mode=show`` возвращает сгенерированный пароль ровно один раз — открытым он
    нигде не хранится; ``mode=mail`` отправляет письмо со ссылкой первого входа.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.tenant_context.membership
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": t("admin.employee_not_found")}, status=404)
        if not can_manage_employee(actor, profile, EmployeeAction.RESET_PASSWORD):
            return deny_employee_action(request, profile, EmployeeAction.RESET_PASSWORD)
        mode = clean_password_mode(request.data.get("mode"))
        if mode is None:
            return Response({"detail": t("admin.unknown_password_mode")}, status=400)
        # Пароль живёт на пользователе, а не на членстве: сбрасывать его из одной
        # организации, когда человек работает и в другой, нельзя.
        if profile.user.memberships.count() > 1:
            return Response(
                {"detail": t("admin.multi_org_self_reset")},
                status=409,
            )
        password = reset_employee_password(
            profile=profile, mode=mode, actor=actor, request=request
        )
        profile.refresh_from_db()
        return Response(
            {"employee": employee_payload(profile, actor), "password": password}
        )


class EmployeeRevokeSessionsView(APIView):
    """Завершение всех сессий сотрудника (кадры E2/E3)."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, user_id: int) -> Response:
        actor = request.tenant_context.membership
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": t("admin.employee_not_found")}, status=404)
        if not can_manage_employee(actor, profile, EmployeeAction.TERMINATE_SESSIONS):
            return deny_employee_action(request, profile, EmployeeAction.TERMINATE_SESSIONS)
        revoked = revoke_user_sessions(profile.user_id)
        record_audit_event(
            action="identity.employee_sessions_terminated",
            actor=request.user,
            organization=profile.organization,
            object_type="HumanUser",
            object_id=str(profile.user_id),
            payload={"sessionsRevoked": revoked},
            request=request,
        )
        return Response({"employee": employee_payload(profile, actor), "revoked": revoked})


class EmployeeBlockView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.tenant_context.membership
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": t("admin.employee_not_found")}, status=404)
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
        actor = request.tenant_context.membership
        profile = get_owned_profile(request, user_id)
        if profile is None:
            return Response({"detail": t("admin.employee_not_found")}, status=404)
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
