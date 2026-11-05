"""HTTP adapters for assignment policy and protected transfer history."""

from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.conversations.assignment_policy import assignment_settings
from chatballs.conversations.models import Conversation
from chatballs.conversations.transfer_queries import transfer_history, transfer_options
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t


class AssignmentPolicyView(APIView):
    permission_classes = [HasCapability]
    required_capability = "settings.manage"

    def get(self, request):
        return Response(assignment_settings(request.tenant_context))

    def put(self, request):
        return Response(assignment_settings(request.tenant_context, request.data))


class TransferHistoryView(ConversationViewBase):
    def get(self, request, conversation_id, transfer_id=None):
        try:
            return Response(transfer_history(request.tenant_context, conversation_id,
                request.query_params, transfer_id=transfer_id))
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)


class TransferOptionsView(ConversationViewBase):
    required_capability = "conversations.assign"

    def get(self, request, conversation_id):
        try:
            return Response(transfer_options(request.tenant_context, conversation_id, request.query_params))
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
