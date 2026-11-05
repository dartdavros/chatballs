"""Mail continuation delegates to the original queue and immutable retry route."""

from dataclasses import replace

from django.core.files.uploadedfile import SimpleUploadedFile

from chatballs.conversations import email_queries
from chatballs.conversations.email_continuation import retry_email_reply, send_email_reply
from chatballs.conversations.email_payloads import attempt_payload, operation_payload
from chatballs.integrations.action_catalog.email_schemas import (
    ATTEMPT,
    OPERATION,
    OPERATIONS,
    OPTIONS,
)
from chatballs.integrations.action_catalog.schema import (
    BOOLEAN,
    CONVERSATION_ID,
    IDENTIFIER,
    TEXT,
    action,
    obj,
    required,
)
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec


def result(data):
    operations = data.get("items", []) + ([data["operation"]] if "operation" in data else [])
    attempts = [attempt for operation in operations for attempt in operation["attempts"]]
    if "attempt" in data:
        attempts.append(data["attempt"])
    for attempt in attempts:
        attempt["state"], attempt["errorCode"] = str(attempt["state"]), str(attempt["errorCode"])
    return OperationResult(ResultState.COMPLETED, data)


def options(context, values):
    context.require_conversation(values["conversation_id"])
    return result(email_queries.options(context.tenant, values["conversation_id"]))


def operations(context, values):
    context.require_conversation(values["conversation_id"])
    return result(email_queries.operations(context.tenant, values["conversation_id"],
        message_ids=values.get("messageIds"), before=values.get("before"), limit=values.get("limit", 50)))


def send(context, values):
    context.require_conversation(values["conversation_id"])
    upload = None
    if values.get("file"):
        name, content_type, content = context.open_file(values["file"]["fileId"])
        upload = SimpleUploadedFile(name, content, content_type)
    operation, _created = send_email_reply(context=context.tenant, conversation_id=values["conversation_id"],
        recipient=values["recipient"], connection_id=values["connectionId"], text=values.get("text", ""),
        client_key=context.effect_key, subject=values.get("subject", ""), upload=upload)
    return result({"operation": operation_payload(operation, context=context.tenant)})


def retry(context, values):
    context.require_conversation(values["conversation_id"])
    attempt = retry_email_reply(context=context.tenant, conversation_id=values["conversation_id"],
        operation_id=values["operation_id"], acknowledge_unknown=values.get("acknowledgeUnknown", False))
    return result({"attempt": attempt_payload(attempt)})


for key, title, fields, output, handler, route, view, method, effect in (
    ("email_options.get", "native.email_options", {}, OPTIONS, options, "options/", "EmailOptionsView", "GET", Effect.READ),
    ("email_operations.get", "native.email_operations", {"messageIds": TypeSpec("array", items=IDENTIFIER, max_items=200),
        "before": TypeSpec("integer"), "limit": TypeSpec("integer")}, OPERATIONS, operations,
        "operations/", "EmailOperationsView", "GET", Effect.READ),
    ("email_operations.post", "native.email_send", {"recipient": required(TEXT),
        "connectionId": replace(IDENTIFIER, title_key="native.fields.connectionId"),
        "text": replace(TEXT, max_length=20000), "subject": replace(TEXT, max_length=998), "file": TypeSpec("file")},
        obj(operation=replace(OPERATION, title_key="native.email_operation")), send, "operations/", "EmailOperationsView", "POST", Effect.CREATE),
    ("email_retry.post", "native.email_retry", {"operation_id": replace(IDENTIFIER, title_key="native.email_operation_id"),
        "acknowledgeUnknown": BOOLEAN}, obj(attempt=replace(ATTEMPT, title_key="native.email_attempt")), retry,
        "operations/<int:operation_id>/retry/", "EmailRetryView", "POST", Effect.CREATE),
):
    action(key=f"messages.{key}", title=title, input=obj(conversation_id=CONVERSATION_ID, **fields),
        output=output, handler=handler, capability="conversations.view" if handler == operations else "conversations.operate",
        scope="conversation", route=f"conversations/<int:conversation_id>/email/{route}",
        view=f"chatballs.conversations.email_views.{view}", method=method, effect=effect)
