"""HTTP adapters for original conversation list, opening and deletion."""

from rest_framework.response import Response

from chatballs.conversations.list_queries import LIST_WINDOW_SIZE as LIST_WINDOW_SIZE
from chatballs.conversations.list_queries import conversation_list
from chatballs.conversations.models import Conversation
from chatballs.conversations.participant_access_loss import access_loss_payload
from chatballs.conversations.read_services import open_conversation, remove_conversation
from chatballs.conversations.serializers import conversation_payload
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t


class ConversationListView(ConversationViewBase):
    def get(self, request):
        return Response(conversation_list(request.tenant_context, request.query_params))


class ConversationDetailView(ConversationViewBase):
    def get(self, request, conversation_id):
        try:
            row = open_conversation(request.tenant_context, conversation_id)
        except Conversation.DoesNotExist:
            return Response(access_loss_payload(request.tenant_context, conversation_id), status=404)
        return Response({"conversation": conversation_payload(row, detailed=True, viewer_id=request.user.pk)})

    def delete(self, request, conversation_id):
        try:
            remove_conversation(request.tenant_context, conversation_id, request=request)
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        return Response(status=204)
