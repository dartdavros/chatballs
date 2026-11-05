"""HTTP adapter for the shared protected participation journal."""

from rest_framework.response import Response

from chatballs.conversations.journal_queries import (
    FIELDS as FIELDS,
)
from chatballs.conversations.journal_queries import (
    journal_payload as journal_payload,
)
from chatballs.conversations.journal_queries import (
    participant_events as participant_events,
)
from chatballs.conversations.journal_queries import (
    participation_journal,
)
from chatballs.conversations.journal_queries import (
    transfer_events as transfer_events,
)
from chatballs.conversations.models import Conversation
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t


class ParticipationJournalView(ConversationViewBase):
    def get(self, request, conversation_id):
        try:
            return Response(participation_journal(request.tenant_context, conversation_id, request.query_params))
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
