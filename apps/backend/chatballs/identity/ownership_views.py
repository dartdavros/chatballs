from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from chatballs.identity.employee_api import response_for
from chatballs.identity.ownership_commands import transfer_ownership


class OwnershipTransferView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        return response_for(transfer_ownership(request.tenant_context, user_id, request.data, request=request))
