"""Visitor observations keep the original visible dialog/session boundary."""

from chatballs.conversations.read_services import visible_conversation
from chatballs.webchat.models import WebSession
from chatballs.webchat.observations import session_observations


def visitor_state(context, conversation_id):
    conversation = visible_conversation(context, conversation_id)
    sessions = WebSession.objects.filter(
        organization_id=conversation.organization_id, connection_id=conversation.connection_id,
        identity__contact_id=conversation.contact_id,
    ).order_by("pk")
    return {"sessions": [session_observations(session) for session in sessions]}
