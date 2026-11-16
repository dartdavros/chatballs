"""Lease/fence around HTTP; planning and response waiting do not hold DB locks."""

import http.client
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from chatballs.ai.execution_policy import execution_guard
from chatballs.ai.external_agents.adapter import clean_address
from chatballs.ai.external_agents.context import prepare
from chatballs.ai.external_agents.contracts import parse
from chatballs.ai.external_agents.handoff import handoff
from chatballs.ai.external_agents.ingress import Conflict, accept
from chatballs.ai.external_agents.json_payloads import dumps
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.send_guards import request_current
from chatballs.ai.external_agents.state import (
    LEASE_SECONDS,
    applicable,
    cancel,
    head,
    lock_conversation,
    schedule,
)
from chatballs.ai.provider.base import ProviderRejected
from chatballs.integrations.adapters.auth import BearerAuth, OutboundRequest
from chatballs.integrations.adapters.contracts import Limits
from chatballs.integrations.adapters.transport import GuardedTransport, TransportError
from chatballs.integrations.outbound import OutboundUrlRejected
from chatballs.integrations.service_connections.binding import load_credentials
from chatballs.tenancy.database import tenant_atomic

RETRIES = (1, 5, 15)
POLLS = (5, 15, 30)


@dataclass(frozen=True)
class Work:
    request_id: str
    fence: int
    request: OutboundRequest
    timeout: float


def abort(row, conversation, context, reason, *, transfer=True):
    cancel(row, context, "expired" if reason == "deadline_exceeded" else "control_revoked")
    if transfer:
        handoff(conversation, context, operation_id=row.public_id, reason=reason)
    row.reason_code = reason
    row.save(update_fields=["reason_code"])


def claim(context, conversation_id):
    conversation = lock_conversation(context, conversation_id)
    if conversation is None:
        return None
    row = head(conversation_id)
    if row is None or row.state == "delivering":
        return None
    now = timezone.now()
    if now >= row.deadline_at:
        abort(row, conversation, context, "deadline_exceeded", transfer=applicable(row, context, deadline=False))
        return None
    if not applicable(row, context):
        expired = timezone.now() >= row.deadline_at
        abort(row, conversation, context, "deadline_exceeded" if expired else "control_revoked",
              transfer=expired and applicable(row, context, deadline=False))
        return None
    if row.next_at > now or row.lease_until and row.lease_until > now:
        return None
    if not row.snapshot_ciphertext and row.trigger.kind == "voice":
        from chatballs.ai.external_agents.voice import claim_voice

        voice = claim_voice(row, conversation, context)
        if voice is not None or row.state == "cancelled":
            return voice
    try:
        prepare(row)
    except ValueError as error:
        abort(row, conversation, context, str(error))
        return None
    now = timezone.now()
    if now >= row.deadline_at:
        abort(row, conversation, context, "deadline_exceeded")
        return None
    polling = row.state in ("accepted", "processing")
    if not polling and row.attempts >= 4:
        abort(row, conversation, context, "service_failed")
        return None
    service = row.session.connection.integration.service_settings
    url = clean_address(service.settings["base_url"]) + "/requests"
    method, body = "POST", dumps(open_payload(row.snapshot_ciphertext)).encode()
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Idempotency-Key": str(row.public_id)}
    if polling:
        method, url, body = "GET", url + "/" + str(row.public_id), None
        row.polls += 1
    else:
        row.attempts += 1
        row.state = "dispatching"
    row.active, row.fence = True, row.fence + 1
    row.lease_until = now + timedelta(seconds=LEASE_SECONDS)
    row.save(update_fields=["attempts", "polls", "state", "active", "fence", "lease_until"])
    schedule(context, conversation_id, at=min(row.lease_until, row.deadline_at))
    request = BearerAuth().prepare(OutboundRequest(method, url, headers=headers, body=body), load_credentials(service), {})
    return Work(str(row.public_id), row.fence, request, min(10, (row.deadline_at - now).total_seconds()))


def retry(row, context, *, retry_after=0):
    if row.state in ("accepted", "processing"):
        delay = POLLS[min(row.polls, 2)]
    elif row.attempts < 4:
        delay = RETRIES[row.attempts - 1]
    else:
        delay = 0
    row.lease_until = None
    now = timezone.now()
    # Bound untrusted Retry-After before constructing timedelta (huge integers
    # must neither overflow nor postpone recovery beyond the original deadline).
    delay = min(max(delay, retry_after), max(0, (row.deadline_at - now).total_seconds()))
    row.next_at = min(row.deadline_at, now + timedelta(seconds=delay))
    row.save(update_fields=["lease_until", "next_at"])
    schedule(context, row.conversation_id, at=row.next_at)


def settle(work, context, response):
    stub = ExternalAgentRequest.objects.filter(public_id=work.request_id).first()
    if stub is None:
        return
    conversation = lock_conversation(context, stub.conversation_id)
    row = ExternalAgentRequest.objects.select_for_update(of=("self",)).select_related("session__connection").get(pk=stub.pk)
    if row.fence != work.fence or row.state in ("terminal", "cancelled", "delivering"):
        return
    if not applicable(row, context):
        expired = timezone.now() >= row.deadline_at
        abort(row, conversation, context, "deadline_exceeded" if expired else "control_revoked",
              transfer=expired and applicable(row, context, deadline=False))
        return
    if response is None or response.status in (408, 429) or response.status >= 500:
        retry_after = 0
        if response:
            try:
                retry_after = max(0, int(response.headers.get("retry-after", response.headers.get("Retry-After", "0"))))
            except ValueError:
                pass
        retry(row, context, retry_after=retry_after)
        return
    try:
        if response.content_type != "application/json" or response.file or response.status not in (200, 202):
            raise ValueError("invalid_request")
        body = parse("result.yaml", "RequestStatus", response.body)
        if body["requestId"] != work.request_id:
            raise ValueError("invalid_request")
        if body["status"] in ("completed", "failed"):
            if response.status != 200:
                raise ValueError("invalid_request")
            with tenant_atomic(context):
                accept(context, row.session.connection, work.request_id, body, fence=work.fence)
            return
        if body["status"] == "cancelled":
            abort(row, conversation, context, "external_outcome_unknown")
            return
        if work.request.method == "POST" and response.status != 202:
            raise ValueError("invalid_request")
        session_id = body["externalSessionId"] or ""
        if row.session.external_session_id and row.session.external_session_id != session_id:
            raise Conflict()
        row.session.external_session_id = session_id
        row.session.save(update_fields=["external_session_id"])
        # An unknown remote outcome is reconciled read-only until the original
        # deadline. Reposting would risk executing business actions again.
        row.state = "accepted" if body["status"] == "unknown" else body["status"]
        row.reason_code = "external_outcome_unknown" if body["status"] == "unknown" else ""
        row.save(update_fields=["state", "reason_code"])
        retry(row, context)
    except (ValueError, Conflict):
        abort(row, conversation, context, "service_failed")


def run(context, conversation_id):
    from chatballs.ai.external_agents.voice import VoiceWork, run_voice

    with tenant_atomic(context):
        work = claim(context, conversation_id)
    if isinstance(work, VoiceWork):
        if not run_voice(work, context):
            return
        with tenant_atomic(context):
            work = claim(context, conversation_id)
    if work is not None:
        try:
            with execution_guard(lambda: request_current(work, context)):
                response = GuardedTransport().send(work.request, limits=Limits(
                    timeout_seconds=work.timeout, max_response_bytes=262144, max_file_bytes=262144,
                ))
        except (ProviderRejected, TransportError, OutboundUrlRejected, OSError, http.client.HTTPException):
            response = None
        with tenant_atomic(context):
            settle(work, context, response)
    from chatballs.ai.external_agents.recovery import cancel_due

    cancel_due(context, conversation_id)
