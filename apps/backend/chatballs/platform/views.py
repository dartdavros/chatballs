"""Platform provisioning retains its own authentication and capability."""
from rest_framework.views import APIView

from chatballs.identity.command_http import command_response
from chatballs.platform.authentication import PlatformTokenAuthentication
from chatballs.platform.commands import provision
from chatballs.platform.permissions import HasPlatformCapability


class OrganizationProvisionView(APIView):
    authentication_classes = [PlatformTokenAuthentication]
    permission_classes = [HasPlatformCapability]
    required_platform_capability = "platform.organizations.provision"

    def post(self, request):
        return command_response(provision(request.user, request.auth, request.data,
            idempotency_key=request.headers.get("Idempotency-Key", "")))
