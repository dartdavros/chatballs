"""HTTP adapters for the original queue policy service."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.conversations.queue_policy_service import FIELDS as FIELDS
from chatballs.conversations.queue_policy_service import MAX_MINUTES as MAX_MINUTES
from chatballs.conversations.queue_policy_service import queue_policy


class QueuePolicyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(queue_policy(request.tenant_context))

    def patch(self, request):
        return Response(queue_policy(request.tenant_context, request.data))
