"""Employee assistance uses its original queue, reply rights and history version."""

from chatballs.ai import assistance_queries
from chatballs.ai.assistance_payload import suggestion_payload
from chatballs.ai.assistance_services import reject_suggestion, request_suggestion
from chatballs.integrations.action_catalog.assistance_schemas import (
    ATTEMPT,
    ATTEMPT_ID,
    SUGGESTION,
    SUGGESTION_ID,
)
from chatballs.integrations.action_catalog.schema import CONVERSATION_ID, action, obj, required
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec


def result(data):
    # Fresh model choice instances have the same JSON representation as the API.
    for key in ("attempt", "suggestion"):
        if key in data:
            normalize(data[key])
    for attempt in data.get("items", []):
        normalize(attempt)
    return OperationResult(ResultState.COMPLETED, data)


def normalize(operation):
    operation["status"], operation["errorCode"] = str(operation["status"]), str(operation["errorCode"])
    for suggestion in operation.get("suggestions", []):
        normalize(suggestion)


def read(context, values):
    context.require_conversation(values["conversation_id"])
    return result(assistance_queries.attempts(context.tenant, values["conversation_id"]))


def detail(context, values):
    context.require_conversation(values["conversation_id"])
    return result(assistance_queries.detail(context.tenant, values["conversation_id"], values["attempt_id"]))


def request(context, values):
    context.require_conversation(values["conversation_id"])
    suggestion = request_suggestion(context=context.tenant, conversation_id=values["conversation_id"],
        key=context.effect_key, attempt_id=values.get("attempt_id"))
    return result({"suggestion": suggestion_payload(suggestion)})


def reject(context, values):
    context.require_conversation(values["conversation_id"])
    suggestion = reject_suggestion(context=context.tenant, conversation_id=values["conversation_id"],
        suggestion_id=values["suggestion_id"])
    return result({"suggestion": suggestion_payload(suggestion)})


for key, title, fields, output, handler, route, view, method in (
    ("assistance.get", "native.assistance_list", {}, obj(items=TypeSpec("array", items=ATTEMPT)), read,
        "reply-assistance/", "AssistanceListView", "GET"),
    ("assistance.post", "native.assistance_request", {"attempt_id": ATTEMPT_ID}, obj(suggestion=SUGGESTION), request,
        "reply-assistance/", "AssistanceListView", "POST"),
    ("assistance_attempt.get", "native.assistance_detail", {"attempt_id": required(ATTEMPT_ID)}, obj(attempt=ATTEMPT), detail,
        "reply-assistance/<uuid:attempt_id>/", "AssistanceDetailView", "GET"),
    ("suggestion.post", "native.assistance_reject", {"suggestion_id": required(SUGGESTION_ID)}, obj(suggestion=SUGGESTION), reject,
        "reply-suggestions/<uuid:suggestion_id>/reject/", "AssistanceRejectView", "POST"),
):
    action(key=f"messages.{key}", title=title, input=obj(conversation_id=CONVERSATION_ID, **fields),
        output=output, handler=handler, capability="conversations.operate", scope="conversation",
        route=f"conversations/<int:conversation_id>/{route}", view=f"chatballs.ai.assistance_views.{view}", method=method)
