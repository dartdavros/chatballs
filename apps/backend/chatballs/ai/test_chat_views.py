"""HTTP boundary of the shared real test-chat operation."""

from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ai.test_chat_service import run_test_chat
from chatballs.api.permissions import HasCapability
from chatballs.tenancy.database import tenant_atomic


class AgentCardTestChatView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"
    tenant_manages_own_transaction = True

    def check_permissions(self, request):
        with tenant_atomic(request.tenant_context):
            super().check_permissions(request)

    def post(self, request, agent_id):
        body = request.data if isinstance(request.data, dict) else {}
        status, payload = run_test_chat(request.tenant_context, agent_id, body)
        return Response(payload, status=status)
