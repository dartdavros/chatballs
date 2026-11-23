from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from chatballs.identity import employee_security_commands as commands
from chatballs.identity.employee_api import response_for
from chatballs.identity.employee_dismissal import dismiss_employee


class EmployeeResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        return response_for(commands.reset_password(request.tenant_context, user_id, request.data, request=request))


class EmployeeRevokeSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        return response_for(commands.revoke_sessions(request.tenant_context, user_id, request.data, request=request))


class EmployeeBlockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        return response_for(commands.block_employee(request.tenant_context, user_id, request.data, request=request))


class EmployeeUnblockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        return response_for(commands.unblock_employee(request.tenant_context, user_id, request.data, request=request))


class EmployeeDismissView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        return response_for(dismiss_employee(request.tenant_context, user_id, request.data, request=request))
