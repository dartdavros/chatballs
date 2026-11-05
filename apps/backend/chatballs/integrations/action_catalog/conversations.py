"""Lifecycle actions call the original services, including their event guards."""

from functools import partial

from chatballs.conversations import services
from chatballs.integrations.action_catalog.resources import (
    CONVERSATION_RESULT,
    audit,
    conversation,
    conversation_result,
)
from chatballs.integrations.action_catalog.schema import CONVERSATION_ID, action, obj
from chatballs.integrations.adapters.contracts import OperationResult, ResultState


def transition(context, values, *, service, audit_action):
    conversation(context.tenant, values["conversation_id"], "conversations.operate")
    row = service(context=context.tenant, conversation_id=values["conversation_id"],
        operation_id=context.effect_key)
    audit(context.tenant, audit_action, row)
    return OperationResult(ResultState.COMPLETED, conversation_result(context.tenant, row))


for key, title, service, audit_action, view, route in (
    ("claim", "native.conversation_claim", services.claim_conversation, "claimed", "ConversationClaimView", "claim"),
    ("release", "native.conversation_release", services.release_to_ai, "released_to_ai", "ConversationReleaseView", "release"),
    ("return_queue", "native.conversation_queue", services.return_to_queue, "returned_to_queue", "ConversationReturnQueueView", "return-queue"),
    ("close", "native.conversation_close", services.close_conversation, "closed", "ConversationCloseView", "close"),
    ("spam", "native.conversation_spam", services.mark_conversation_as_spam, "marked_spam", "ConversationSpamView", "spam"),
):
    action(key=f"conversations.{key}.post", title=title,
        input=obj(conversation_id=CONVERSATION_ID), output=CONVERSATION_RESULT,
        handler=partial(transition, service=service, audit_action=audit_action),
        capability="conversations.operate", scope="conversation",
        route=f"conversations/<int:conversation_id>/{route}/",
        view=f"chatballs.conversations.lifecycle_views.{view}", method="POST")
