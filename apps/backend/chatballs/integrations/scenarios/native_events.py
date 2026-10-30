"""Declared Chatballs launch contracts. Event delivery is implemented by T-172."""

from chatballs.integrations.adapters.schema import TypeSpec

CONVERSATION_EVENT = TypeSpec("object", properties=(
    ("conversationId", TypeSpec("integer", required=True, title_key="scenarios.conversation")),
    ("contactId", TypeSpec("integer", nullable=True, title_key="scenarios.contact")),
))
NATIVE_EVENTS = (
    ("conversation.started", "scenarios.event_started", CONVERSATION_EVENT),
    ("conversation.tag_added", "scenarios.event_tag_added", TypeSpec("object", properties=CONVERSATION_EVENT.properties + (
        ("tagId", TypeSpec("integer", required=True, title_key="scenarios.tag")),
    ))),
    ("conversation.closed", "scenarios.event_closed", CONVERSATION_EVENT),
)
