"""Visible inbox and conversation opening/deletion call the product services."""

from chatballs.conversations.list_queries import conversation_list
from chatballs.conversations.message_history import message_history
from chatballs.conversations.read_services import open_conversation, remove_conversation
from chatballs.integrations.action_catalog.message_schemas import MESSAGE, WINDOW_INPUTS, window_of
from chatballs.integrations.action_catalog.resources import (
    CONVERSATION,
    CONVERSATION_RESULT,
    conversation,
    conversation_result,
)
from chatballs.integrations.action_catalog.schema import (
    BOOLEAN,
    CONVERSATION_ID,
    TEXT,
    action,
    enum,
    obj,
)
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec


def listing(context, values):
    # Preserve scalar search/filter values; only the product's boolean flags use 1/0.
    params = {key: ("1" if value else "0") if isinstance(value, bool) else value for key, value in values.items()}
    return OperationResult(ResultState.COMPLETED, conversation_list(context.tenant, params))


def get(context, values):
    row = open_conversation(context.tenant, values["conversation_id"])
    return OperationResult(ResultState.COMPLETED, conversation_result(context.tenant, row))


def delete(context, values):
    remove_conversation(context.tenant, values["conversation_id"])
    return OperationResult(ResultState.COMPLETED, {})


def messages(context, values):
    row = conversation(context.tenant, values["conversation_id"])
    return OperationResult(ResultState.COMPLETED, message_history(row, values))


action(key="conversations.get", title="native.conversations_list", input=obj(archived=BOOLEAN,
    group=TypeSpec("string", pattern=r"none|[1-9]\d*"), agent=TypeSpec("string", pattern=r"[1-9]\d*"),
    lifecycle=CONVERSATION.field("lifecycle"), assigned=TypeSpec("string", pattern=r"me|[1-9]\d*"),
    waiting=BOOLEAN, queue=BOOLEAN, waitingOnMe=BOOLEAN, q=TEXT,
    sort=enum(("activity", "waiting"), "native.conversation_sort"), cursor=TypeSpec("integer"), limit=TypeSpec("integer")),
    output=window_of(CONVERSATION, total=TypeSpec("integer")), handler=listing,
    capability="conversations.view", scope="organization", route="conversations/",
    view="chatballs.conversations.read_views.ConversationListView", method="GET")

for key, title, handler, output, method in (
    ("conversations.detail.get", "native.conversation_read", get, CONVERSATION_RESULT, "GET"),
    ("conversations.detail.delete", "native.conversation_delete", delete, obj(), "DELETE"),
):
    action(key=key, title=title, input=obj(conversation_id=CONVERSATION_ID), output=output, handler=handler,
        capability="conversations.view" if method == "GET" else "conversations.operate", scope="conversation",
        route="conversations/<int:conversation_id>/", view="chatballs.conversations.read_views.ConversationDetailView", method=method)

action(key="messages.get", title="native.messages_history", input=obj(conversation_id=CONVERSATION_ID, **WINDOW_INPUTS),
    output=window_of(MESSAGE), handler=messages, capability="conversations.view", scope="conversation",
    route="conversations/<int:conversation_id>/messages/", view="chatballs.conversations.message_views.ConversationMessageView", method="GET")
