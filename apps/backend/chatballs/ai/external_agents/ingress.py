"""One transactional terminal transition for synchronous responses and callbacks."""

from uuid import uuid4

from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import APIException

from chatballs.ai.external_agents.accepted_delivery import accept_delivery
from chatballs.ai.external_agents.canonical import digest
from chatballs.ai.external_agents.contracts import validate
from chatballs.ai.external_agents.handoff import handoff
from chatballs.ai.external_agents.normalization import normalize
from chatballs.ai.external_agents.payloads import seal
from chatballs.ai.external_agents.receipt_models import ExternalAgentReceipt, ExternalAgentTombstone
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.state import (
    applicable,
    finish,
    lock_conversation,
)


class Conflict(APIException):
    status_code = 409
    default_code = "result_conflict"


def control_ack(request_id, state, reason):
    return {"version": "1", "requestId": str(request_id), "receiptId": str(uuid4()),
            "state": state, "reasonCode": reason, "deliveryId": None, "items": []}


def accept(context, connection, request_id, body, *, fence=None):
    """Caller commits the tenant transaction before exposing the returned ACK."""
    validate("result.yaml", "TerminalResult", body)
    if body["requestId"] != str(request_id):
        raise Conflict()
    row = ExternalAgentRequest.objects.filter(public_id=request_id, session__connection=connection).first()
    if row is not None:
        conversation = lock_conversation(context, row.conversation_id)
        row = ExternalAgentRequest.objects.select_for_update(of=("self",)).select_related(
            "session__connection", "trigger", "conversation__contact",
        ).get(pk=row.pk)
    else:
        conversation = None
    tombstone = ExternalAgentTombstone.objects.select_for_update().filter(
        request_id=request_id, connection=connection,
    ).first()
    if tombstone is None:
        raise Http404
    hashed = digest(connection.deduplication_key, operation="submitExternalAgentResult",
                    route=[str(connection.pk), str(request_id)], body=body)
    if tombstone.digest:
        if tombstone.digest != hashed:
            raise Conflict()
        return tombstone.ack, 200
    if ExternalAgentTombstone.objects.filter(connection=connection, result_id=body["resultId"]).exists():
        raise Conflict()
    if fence is not None and row is not None and row.fence != fence:
        return None, 200
    applies = row is not None and row.state != "cancelled" and row.active and applicable(row, context)
    if applies and body["status"] == "completed":
        session_id = body["externalSessionId"] or ""
        if row.session.external_session_id and row.session.external_session_id != session_id:
            raise Conflict()
        outcome = body["outcome"]
        if outcome["type"] == "reply":
            normalized = normalize(row, outcome["messages"])
        row.session.external_session_id = session_id
        row.session.save(update_fields=["external_session_id"])
    if not applies:
        ack = control_ack(request_id, "suppressed", "expired" if row and row.deadline_at <= timezone.now() else "control_revoked")
        status = 200
        if conversation is not None and conversation.control_mode == "HUMAN":
            from chatballs.ai.external_agents.notice_models import ExternalAgentNotice

            ExternalAgentNotice.objects.get_or_create(conversation=conversation, operation_id=request_id,
                                                      kind="suppressed")
    elif body["status"] == "failed":
        ack = control_ack(request_id, "failed", body["error"]["code"])
        handoff(conversation, context, operation_id=request_id, reason="service_failed")
        finish(row, context, reason=body["error"]["code"])
        status = 200
    elif body["outcome"]["type"] == "handoff":
        outcome = body["outcome"]
        ack = control_ack(request_id, "handed_off", outcome["reasonCode"])
        handoff(conversation, context, operation_id=request_id, summary=outcome["summary"])
        finish(row, context)
        status = 200
    else:
        ack, status = accept_delivery(context, row, conversation, normalized)
    validate("receipts.yaml", "Receipt", ack)
    tombstone.digest, tombstone.result_id, tombstone.ack = hashed, body["resultId"], ack
    tombstone.save(update_fields=["digest", "result_id", "ack"])
    if row is not None:
        ExternalAgentReceipt.objects.create(public_id=ack["receiptId"], request=row, result_id=body["resultId"], digest=hashed,
                                            payload_ciphertext=seal(body) if applies else "", ack=ack)
        if not applies and row.state not in ("terminal", "cancelled"):
            if timezone.now() >= row.deadline_at and applicable(row, context, deadline=False):
                handoff(conversation, context, operation_id=request_id, reason="deadline_exceeded")
            finish(row, context, reason="control_revoked", cancelled=True)
    return ack, status
