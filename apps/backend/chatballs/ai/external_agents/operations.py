"""Serialized admission and durable identities for unsolicited protocol operations."""

from django.http import Http404
from rest_framework.exceptions import PermissionDenied

from chatballs.ai.external_agents.auth import _current, authorize_session
from chatballs.ai.external_agents.canonical import digest
from chatballs.ai.external_agents.ingress import Conflict
from chatballs.ai.external_agents.operation_models import ExternalAgentOperation
from chatballs.ai.external_agents.readiness import consent_current
from chatballs.ai.external_agents.session_models import ExternalAgentSession


def identity(context, connection, conversation_id, body, operation):
    session = ExternalAgentSession.objects.filter(
        connection=connection, conversation_id=conversation_id, agent_id=body["agentId"],
        authorization_id=body["authorizationId"], organization_id=context.organization_id,
    ).first()
    if session is None or (session.external_session_id or None) != body["externalSessionId"]:
        raise Http404
    # Also locks the conversation for receipt lookup, admission and publication.
    _, _, conversation, _, versions = _current(
        context, connection, session.agent_id, conversation_id, require_control=False)
    identifier = body["deliveryId" if operation == "messages" else "eventId"]
    hashed = digest(connection.deduplication_key,
        operation="sendExternalAgentMessages" if operation == "messages" else "requestExternalAgentHandoff",
        route=[str(connection.pk), str(conversation_id)], body=body)
    previous = ExternalAgentOperation.objects.filter(
        session=session, operation=operation, public_id=identifier,
    ).first()
    if previous and operation == "handoff":
        # Control was lost, so only the exact resulting generation can receive
        # this content-free ACK. No authority or general read access is restored.
        if (previous.post_versions != versions or previous.authorization_id != session.authorization_id
                or not consent_current(conversation)):
            raise PermissionDenied(code="control_changed")
        if previous.digest != hashed:
            raise Conflict(code="idempotency_conflict")
        return session, conversation, previous, hashed
    authorize_session(context, connection, conversation_id=conversation_id,
        authorization_id=body["authorizationId"], operation=operation)
    if previous and previous.digest != hashed:
        raise Conflict(code="idempotency_conflict")
    return session, conversation, previous, hashed


def remember(session, body, operation, hashed, ack, *, post_versions=None):
    ExternalAgentOperation.objects.create(session=session, operation=operation,
        public_id=body["deliveryId" if operation == "messages" else "eventId"],
        authorization_id=session.authorization_id, digest=hashed, ack=ack,
        post_versions=post_versions or {})
