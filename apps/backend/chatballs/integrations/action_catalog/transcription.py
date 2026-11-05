"""Preserve the source transcription prepare → I/O → store boundary."""

import json
from dataclasses import replace

from django.core.exceptions import ObjectDoesNotExist

from chatballs.ai.provider.base import ProviderError
from chatballs.conversations import transcription as service
from chatballs.conversations.media_queries import visible_message
from chatballs.conversations.models import MessageKind, TranscriptStatus
from chatballs.conversations.serializers import message_payload
from chatballs.integrations.action_catalog.contracts import (
    NativeAccessDenied,
    NativeOperationRejected,
)
from chatballs.integrations.action_catalog.message_schemas import MESSAGE
from chatballs.integrations.action_catalog.schema import IDENTIFIER, action, obj
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.tenancy.database import tenant_atomic


def result(message):
    return OperationResult(ResultState.COMPLETED, json.loads(json.dumps({"message": message_payload(message)})))


def transcribe(context, values):
    rejection = None
    with tenant_atomic(context.tenant):
        try:
            message = visible_message(context.tenant, values["message_id"])
            context.require_conversation(message.conversation_id)
        except ObjectDoesNotExist:
            raise NativeAccessDenied("context") from None
        if message.kind != MessageKind.VOICE or not message.audio:
            raise NativeOperationRejected("arguments")
        if message.transcript_status == TranscriptStatus.READY:
            return result(message)
        if message.audio.size > context.max_file_bytes:
            raise NativeOperationRejected("arguments")
        try:
            job = service.prepare_transcription(message.conversation.channel, message)
        except ProviderError:
            service.mark_transcription_failed(message)
            job, rejection = None, "operation_rejected"
        if job is None:
            rejection = rejection or "context"
    if rejection:
        raise NativeOperationRejected(rejection)
    try:
        transcript = service.run_transcription(job)
    except ProviderError:
        with tenant_atomic(context.tenant):
            service.mark_transcription_failed(message)
        # The source records failure, but a dispatched provider call may have
        # consumed resources. No generic error authorizes an automatic resend.
        raise
    with tenant_atomic(context.tenant):
        service.store_transcription(message, transcript)
        completed = result(message)
    if not transcript:
        raise NativeOperationRejected("operation_rejected")
    return completed


action(key="messages.transcription.post", title="native.transcribe_message",
    input=obj(message_id=replace(IDENTIFIER, title_key="native.fields.message_id")),
    output=obj(message=MESSAGE), handler=transcribe, capability="conversations.view", scope="conversation",
    route="conversations/messages/<int:message_id>/transcribe/",
    view="chatballs.conversations.voice_views.MessageTranscribeView", method="POST", execution="io")
