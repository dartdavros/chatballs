"""Internal comments use the same audience/access and append service as HTTP."""

from chatballs.conversations.comment_services import create_comment
from chatballs.integrations.action_catalog.schema import (
    CONVERSATION_ID,
    TEXT,
    action,
    obj,
    required,
)
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec

COMMENT = obj(id=TypeSpec("integer"), text=TEXT,
    audience=TypeSpec("enum", options=(EnumOption("INTERNAL", "native.audience_internal"),)),
    conversationId=TypeSpec("integer"), operationId=TEXT,
    author=obj(id=TypeSpec("integer"), name=TEXT, avatarUrl=TypeSpec("string", nullable=True)),
    createdAt=TypeSpec("datetime"))


def append(context, values):
    row, _ = create_comment(context=context.tenant,
        conversation_id=values["conversation_id"], audience="INTERNAL",
        text=values["text"], operation_id=context.effect_key)
    from chatballs.conversations.comment_history import comment_payload
    return OperationResult(ResultState.COMPLETED, {"comment": comment_payload(row)})


def history(context, values):
    from chatballs.conversations.comment_history import comment_history
    return OperationResult(ResultState.COMPLETED, comment_history(context=context.tenant,
        conversation_id=values["conversation_id"], parameters=values))


_ROUTE = "conversations/<int:conversation_id>/comments/"
_VIEW = "chatballs.conversations.comment_views.ConversationCommentsView"
action(key="comments.post", title="comments.add", input=obj(
    conversation_id=CONVERSATION_ID, text=required(TEXT)), output=obj(comment=COMMENT),
    handler=append, capability="conversations.comment", scope="conversation",
    route=_ROUTE, view=_VIEW, method="POST")
action(key="comments.get", title="comments.title", input=obj(
    conversation_id=CONVERSATION_ID, after=TypeSpec("integer"), before=TypeSpec("integer"), limit=TypeSpec("integer")),
    output=obj(items=TypeSpec("array", items=COMMENT), hasMore=TypeSpec("boolean"), cursor=TypeSpec("integer", nullable=True)),
    handler=history, capability="conversations.view", scope="conversation",
    route=_ROUTE, view=_VIEW, method="GET")
