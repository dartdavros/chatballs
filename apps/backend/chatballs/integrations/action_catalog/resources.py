"""Resource lookup always starts with the domain's current visibility rules."""

from dataclasses import replace

from chatballs.conversations.access import require_conversation_action
from chatballs.conversations.selectors import conversation_for_context
from chatballs.conversations.serializers import conversation_payload
from chatballs.integrations.action_catalog.schema import obj
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec

# Public payloads retain their complete data. Explicit fields support typed
# references; their evolving presentation metadata is not an input wildcard.
CONVERSATION = replace(obj(id=TypeSpec("integer"), lifecycle=TypeSpec("enum", options=tuple(
    EnumOption(value, f"scenarios.status_{value.lower()}") for value in ("OPEN", "CLOSED", "SPAM"))),
    contact=replace(obj(id=TypeSpec("integer"), name=TypeSpec("string"),
        phone=TypeSpec("string"), email=TypeSpec("string")), nullable=True, open=True)), open=True)
CONVERSATION_RESULT = obj(conversation=CONVERSATION)


def conversation(context, conversation_id, capability="conversations.view"):
    row = conversation_for_context(context=context, conversation_id=conversation_id)
    require_conversation_action(context, row, capability)
    return row


def conversation_result(context, row):
    return {"conversation": conversation_payload(row, detailed=True, viewer_id=context.actor_user.pk)}


def audit(context, action, row):
    from chatballs.identity.audit import record_audit_event
    record_audit_event(action=f"conversations.{action}", actor=context.actor_user,
        organization=context.organization, object_type="Conversation", object_id=str(row.pk))
