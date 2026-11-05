"""HTTP adapters for existing shared-library permissions."""

from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.conversations import template_permissions as service


class TemplatePermissionsView(APIView):
    permission_classes = [HasCapability]
    required_capability = "conversations.view"

    def get(self, request):
        return Response(service.library_permissions(request.tenant_context))


class TemplateManagementGrantView(APIView):
    permission_classes = [HasCapability]
    required_capability = "conversations.view"

    def get(self, request, membership_id):
        return Response(service.management_grant(request.tenant_context, membership_id))

    def patch(self, request, membership_id):
        return Response(service.set_management_grant(request.tenant_context, membership_id,
            request.data, request=request))
