"""Native STT outside transactions; a durable checkpoint prevents blind retries."""

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from chatballs.ai.execution_policy import execution_guard
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.send_guards import request_current
from chatballs.ai.external_agents.state import (
    LEASE_SECONDS,
    applicable,
    lock_conversation,
    schedule,
)
from chatballs.ai.provider.base import ProviderError
from chatballs.conversations.models import TranscriptStatus
from chatballs.conversations.transcription import (
    mark_transcription_failed,
    prepare_transcription,
    run_transcription,
    store_transcription,
)
from chatballs.speech.routing import selected_integration
from chatballs.tenancy.database import tenant_atomic


@dataclass(frozen=True)
class VoiceWork:
    request_id: str
    fence: int
    job: object


def claim_voice(row, conversation, context):
    from chatballs.ai.external_agents.dispatch import abort

    message = row.trigger
    try:
        channel = conversation.channel
        if channel.ai_agent.transcription_integration_id is None:
            raise ValueError("history_content_unavailable")
        selected_integration(channel)
        if message.transcript_status == TranscriptStatus.READY and message.transcript.strip():
            return None
        if row.reason_code == "transcription_pending" or message.transcript_status == TranscriptStatus.FAILED:
            raise ValueError("history_content_unavailable")
        job = prepare_transcription(channel, message,
                                    timeout=min(10, (row.deadline_at - timezone.now()).total_seconds()))
        if job is None:
            raise ValueError("history_content_unavailable")
    except (ProviderError, OSError, ValueError):
        mark_transcription_failed(message)
        abort(row, conversation, context, "history_content_unavailable")
        return None
    row.active, row.state, row.fence = True, "dispatching", row.fence + 1
    row.reason_code = "transcription_pending"
    row.lease_until = timezone.now() + timedelta(seconds=LEASE_SECONDS)
    row.save(update_fields=["active", "state", "fence", "reason_code", "lease_until"])
    schedule(context, conversation.pk, at=min(row.lease_until, row.deadline_at))
    return VoiceWork(str(row.public_id), row.fence, job)


def run_voice(work, context):
    from chatballs.ai.external_agents.dispatch import abort

    try:
        with execution_guard(lambda: request_current(work, context)):
            if not request_current(work, context):
                return False
            transcript = run_transcription(work.job)
    except (ProviderError, OSError):
        transcript = ""
    with tenant_atomic(context):
        stub = ExternalAgentRequest.objects.filter(public_id=work.request_id).first()
        if stub is None:
            return False
        conversation = lock_conversation(context, stub.conversation_id)
        row = ExternalAgentRequest.objects.select_for_update(of=("self",)).select_related("session__connection", "trigger").get(pk=stub.pk)
        if row.fence != work.fence or row.state != "dispatching":
            return False
        if not applicable(row, context):
            abort(row, conversation, context, "control_revoked", transfer=False)
            return False
        if not transcript.strip():
            mark_transcription_failed(row.trigger)
            abort(row, conversation, context, "history_content_unavailable")
            return False
        store_transcription(row.trigger, transcript)
        row.state, row.reason_code, row.lease_until = "queued", "", None
        row.save(update_fields=["state", "reason_code", "lease_until"])
        return True
