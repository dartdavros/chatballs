"""Public replies call source commands; a database message is not delivery."""

import json
from dataclasses import replace

from django.core.files.uploadedfile import SimpleUploadedFile

from chatballs.conversations.attachment_send import send_attachment_reply
from chatballs.conversations.delivery_observation import capture_delivery
from chatballs.conversations.operator_reply import send_contact_request, send_text_reply
from chatballs.conversations.reply_problems import ReplyProblem
from chatballs.conversations.serializers import message_payload
from chatballs.conversations.voice_send import send_voice_reply
from chatballs.integrations.action_catalog.contracts import NativeOperationRejected
from chatballs.integrations.action_catalog.message_schemas import MESSAGE
from chatballs.integrations.action_catalog.schema import (
    BOOLEAN,
    CONVERSATION_ID,
    TEXT,
    action,
    obj,
    required,
)
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.tenancy.database import tenant_atomic

OUTPUT = obj(message=MESSAGE, published=BOOLEAN,
    transportAccepted=replace(BOOLEAN, nullable=True), deliveryConfirmed=BOOLEAN)


def upload(context, reference):
    name, content_type, content = context.open_file(reference["fileId"])
    return SimpleUploadedFile(name, content, content_type)


def execute(context, values, command, **arguments):
    context.require_conversation(values["conversation_id"])
    with capture_delivery() as delivery:
        try:
            # This is the source application-service transaction, not a runner
            # root/checkpoint transaction. Deferred suggestion delivery runs at
            # its original commit boundary, inside the observation scope.
            with tenant_atomic(context.tenant):
                outcome = command(context=context.tenant,
                    conversation_id=int(values["conversation_id"]),
                    operation_id=context.effect_key, **arguments)
        except Exception:
            if not delivery.attempted:
                raise NativeOperationRejected("operation_rejected") from None
            raise
    if isinstance(outcome, ReplyProblem):
        if not delivery.attempted:
            raise NativeOperationRejected("operation_rejected")
        raise RuntimeError("outcome_unavailable")
    if delivery.attempted and not delivery.accepted:
        # The source may have committed a message despite a transport refusal.
        # Preserve that fact; never issue a second delivery from generic retry.
        raise RuntimeError("outcome_unavailable")
    with tenant_atomic(context.tenant):
        data = json.loads(json.dumps(message_payload(outcome)))
    return OperationResult(ResultState.COMPLETED, {"message": data, "published": True,
        "transportAccepted": delivery.accepted if delivery.attempted else None,
        "deliveryConfirmed": False})


def text(context, values):
    return execute(context, values, send_text_reply, text=values["text"],
        suggestion_id=values.get("suggestionId"), suggestion_key=context.effect_key)


def contact(context, values):
    return execute(context, values, send_contact_request)


def voice(context, values):
    return execute(context, values, send_voice_reply, upload=upload(context, values["audio"]),
        duration=values.get("duration", 0))


def attachment(context, values):
    return execute(context, values, send_attachment_reply, upload=upload(context, values["file"]),
        text=values.get("text", ""))


for key, title, fields, handler, suffix, view in (
    ("messages.post", "native.message_send", {"text": required(TEXT),
        "suggestionId": TypeSpec("string")}, text, "messages/", "message_views.ConversationMessageView"),
    ("messages.request_contact.post", "native.contact_request", {}, contact,
        "request-contact/", "message_views.ConversationRequestContactView"),
    ("messages.voice.post", "native.voice_send", {"audio": TypeSpec("file", required=True),
        "duration": TypeSpec("integer")}, voice, "voice/", "voice_views.ConversationVoiceView"),
    ("messages.attachment.post", "native.attachment_send", {"file": TypeSpec("file", required=True),
        "text": replace(TEXT, max_length=4000)}, attachment, "attachments/", "attachment_views.ConversationAttachmentView"),
):
    action(key=key, title=title, input=obj(conversation_id=CONVERSATION_ID, **fields),
        output=OUTPUT, handler=handler, capability="conversations.operate", scope="conversation",
        route=f"conversations/<int:conversation_id>/{suffix}",
        view=f"chatballs.conversations.{view}", method="POST", execution="io", effect=Effect.CREATE)
