from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.integrations.management import address


class HttpAddressValidationView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"POST": "integrations.manage"}

    def post(self, request):
        return Response(address(request.tenant_context, request.data))
