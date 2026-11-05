"""HTTP communication feature settings."""

from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.integrations.communication_settings import read_communication, update_communication


class CommunicationSettingsView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "settings.view", "PATCH": "company.manage"}

    def get(self, request):
        return Response(read_communication(request.tenant_context))

    def patch(self, request):
        return Response(update_communication(request.tenant_context, request.data, request=request))
