"""Explicit conversation metadata actions use the original domain services."""

from chatballs.conversations import metadata_services as service
from chatballs.conversations.contact_card import CARD_LIMITS
from chatballs.conversations.models import ConversationPriority
from chatballs.integrations.action_catalog.resources import CONVERSATION_RESULT, conversation_result
from chatballs.integrations.action_catalog.schema import (
    BOOLEAN,
    CONVERSATION_ID,
    action,
    enum,
    obj,
    required,
)
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec

CARD_FIELDS = {name: TypeSpec("string", max_length=limit) for name, limit in CARD_LIMITS.items()}
PRIORITY = enum(ConversationPriority.values, "native.priority")


def result(context, row):
    return OperationResult(ResultState.COMPLETED, conversation_result(context.tenant, row))


def priority(context, values):
    return result(context, service.set_priority(context.tenant, values["conversation_id"], values["priority"]))


def contact(context, values):
    return result(context, service.change_contact(context.tenant, values["conversation_id"],
        {key: value for key, value in values.items() if key in CARD_FIELDS}))


def note(context, values):
    return result(context, service.set_note(context.tenant, values["conversation_id"], values.get("note", "")))


def labels(context, values):
    return result(context, service.set_labels(context.tenant, values["conversation_id"], values["labelIds"]))


def archive(context, values):
    return result(context, service.set_archived(context.tenant, values["conversation_id"], values["archived"]))


for key, title, inputs, handler, route, view, capability in (
    ("conversations.priority.post", "native.conversation_priority", obj(conversation_id=CONVERSATION_ID,
        priority=required(PRIORITY)), priority, "priority/", "ConversationPriorityView", "conversations.operate"),
    ("contacts.from_conversation.post", "native.conversation_contact", obj(conversation_id=CONVERSATION_ID,
        **CARD_FIELDS), contact, "contact/", "ConversationContactView", "conversations.operate"),
    ("conversations.note.post", "native.conversation_note", obj(conversation_id=CONVERSATION_ID,
        note=TypeSpec("string", max_length=4000)), note, "note/", "ConversationNoteView", "conversations.comment"),
    ("conversations.labels.post", "native.conversation_labels", obj(conversation_id=CONVERSATION_ID,
        labelIds=required(TypeSpec("array", items=TypeSpec("integer")))), labels, "labels/", "ConversationLabelsView", "conversations.operate"),
    ("conversations.archive.post", "native.conversation_archive", obj(conversation_id=CONVERSATION_ID,
        archived=required(BOOLEAN)), archive, "archive/", "ConversationArchiveView", "conversations.operate"),
):
    action(key=key, title=title, input=inputs, output=CONVERSATION_RESULT, handler=handler,
        capability=capability, scope="conversation", route=f"conversations/<int:conversation_id>/{route}",
        view=f"chatballs.conversations.conversation_metadata_views.{view}", method="POST")
