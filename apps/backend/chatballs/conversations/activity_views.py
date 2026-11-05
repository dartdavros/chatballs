"""HTTP adapter for the shared protected activity timeline."""

from rest_framework.response import Response

from chatballs.conversations.activity_queries import HistoryInput as HistoryInput
from chatballs.conversations.activity_queries import activity_payload as activity_payload
from chatballs.conversations.activity_queries import conversation_activity
from chatballs.conversations.activity_queries import person as person
from chatballs.conversations.models import Conversation
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t


class ConversationActivityView(ConversationViewBase):
    def get(self, request, conversation_id):
        try:
            return Response(conversation_activity(request.tenant_context, conversation_id, request.query_params))
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
