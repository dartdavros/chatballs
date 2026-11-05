"""Visitor observations are scoped to the visible dialog and its contact's WebSessions."""

from rest_framework.response import Response

from chatballs.conversations.models import Conversation
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.conversations.visitor_state_queries import visitor_state
from chatballs.i18n import t


class VisitorStateView(ConversationViewBase):
    def get(self, request, conversation_id):
        try:
            return Response(visitor_state(request.tenant_context, conversation_id))
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
