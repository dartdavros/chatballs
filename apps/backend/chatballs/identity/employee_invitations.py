"""HTTP invitation commands share the application services with automation."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from chatballs.identity.employee_api import response_for
from chatballs.identity.employee_invitation_commands import resend, revoke


class InvitationResendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, invitation_id):
        return response_for(resend(request.tenant_context, invitation_id, request=request))


class InvitationRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, invitation_id):
        return response_for(revoke(request.tenant_context, invitation_id, request=request))
