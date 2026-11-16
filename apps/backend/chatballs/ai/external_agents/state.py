"""Short transactional transitions shared by dispatch, ingress and recovery."""

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from chatballs.ai.external_agents.auth import authorize_session, issue_authorization
from chatballs.ai.external_agents.canonical import digest
from chatballs.ai.external_agents.payloads import open_payload, seal
from chatballs.ai.external_agents.receipt_models import ExternalAgentTombstone
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.conversations.ai_reply_delivery import reply_route
from chatballs.conversations.models import AiTurnState, Conversation, Message
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.identity.operation_modes import lock_organization
from chatballs.integrations.models import Integration
from chatballs.tenancy.context import TenantContext

WAKE = "external_agent.wake"
DELIVER = "external_agent.deliver"
LEASE_SECONDS = 20
FINAL = ("terminal", "cancelled")


def schedule(context, conversation_id, *, at=None, event_type=WAKE):
    enqueue_event(DomainEvent(
        # FIFO belongs to the durable request checkpoint. A crashed outbox job's
        # generic 300s lease must not block the request's own recovery/deadline.
        aggregate_type="ExternalAgentJob", aggregate_id=str(uuid4()),
        event_type=event_type, payload={"conversationId": conversation_id},
        tenant_context=TenantContext.for_resource(context.organization, correlation_id=context.correlation_id),
    ), available_at=at)


def lock_conversation(context, conversation_id):
    lock_organization(context.organization_id)
    return Conversation.including_tests.select_for_update(of=("self",)).select_related(
        "channel__ai_agent", "connection", "contact",
    ).filter(pk=conversation_id, organization_id=context.organization_id).first()


def enqueue(message, user_id, context):
    """Called in the inbox transaction; duplicates cannot replace the trigger."""
    conversation = lock_conversation(context, message.conversation_id)
    message = Message.including_tests.select_for_update().get(pk=message.pk, conversation=conversation)
    # Operational checkpoints expire; the persisted trigger still names its
    # lifetime tombstone and can never be turned into a fresh business request.
    previous_id = message.ai_delivery.get("externalRequestId")
    if previous_id and ExternalAgentTombstone.objects.filter(request_id=previous_id).exists():
        return
    if ExternalAgentRequest.objects.filter(trigger=message).exists():
        return
    agent = conversation.channel.ai_agent
    connection = agent.external_binding.connection
    session = issue_authorization(context, connection, agent.pk, conversation.pk)
    binding = agent.external_binding
    timeout = binding.long_timeout if binding.processing_mode == "long" else binding.ordinary_timeout
    route = reply_route(SimpleNamespace(message=message, conversation=conversation, user_id=user_id))
    if conversation.is_test:
        from chatballs.ai.external_agents.test_scope import test_route

        route = test_route(conversation)
    transport = Integration.objects.filter(pk=route["connectionId"]).first()
    route["transportVersion"] = transport.runtime_revision if transport else None
    seed = {"userId": user_id, "text": message.text, "kind": message.kind,
            "createdAt": message.created_at.isoformat(), "route": route}
    row = ExternalAgentRequest.objects.create(
        session=session, conversation=conversation, trigger=message,
        authorization_id=session.authorization_id, authorization_versions=session.authorization_versions,
        sequence=message.pk, deadline_at=message.created_at + timedelta(seconds=min(timeout, binding.maximum_timeout)),
        next_at=timezone.now(), seed_ciphertext=seal(seed),
    )
    ExternalAgentTombstone.objects.create(connection=connection, request_id=row.public_id,
        trigger_digest=digest(connection.deduplication_key, operation="externalAgentTrigger",
                              route=[str(connection.pk), str(conversation.pk), str(message.pk)], body=seed))
    message.ai_turn_state = AiTurnState.PENDING
    message.ai_delivery = {"modeVersion": session.authorization_versions["operation"],
                           "externalRequestId": str(row.public_id)}
    message.save(update_fields=["ai_turn_state", "ai_delivery"])
    schedule(context, conversation.pk)


def current(row, context, *, deadline=True):
    if deadline and timezone.now() >= row.deadline_at:
        raise PermissionDenied(code="expired")
    if row.authorization_id != row.session.authorization_id:
        raise PermissionDenied(code="control_changed")
    authorize_session(context, row.session.connection, conversation_id=row.conversation_id,
                      authorization_id=row.authorization_id, operation="results")
    if ExternalAgentRequest.objects.filter(
        conversation_id=row.conversation_id, sequence__lt=row.sequence,
    ).exclude(state__in=FINAL).exists():
        raise PermissionDenied(code="conversation_busy")
    if row.authorization_versions != row.session.authorization_versions:
        raise PermissionDenied(code="control_changed")
    route = open_payload(row.seed_ciphertext)["route"]
    if row.conversation.is_test:
        if route.get("testScope") != row.authorization_versions.get("testScope"):
            raise PermissionDenied(code="control_changed")
        return
    transport = Integration.objects.filter(pk=route["connectionId"], organization_id=context.organization_id).first()
    if transport is None or not transport.is_active or transport.runtime_revision != route["transportVersion"]:
        raise PermissionDenied(code="channel_restricted")
    if transport.provider not in {"WEB", "EMAIL", "TELEGRAM", "MAX", "VK"}:
        raise PermissionDenied(code="channel_restricted")


def applicable(row, context, *, deadline=True):
    try:
        current(row, context, deadline=deadline)
        return True
    except (PermissionDenied, Http404):
        return False


def finish(row, context, *, reason="", cancelled=False):
    row.state = "cancelled" if cancelled else "terminal"
    row.active = False
    row.lease_until = None
    row.terminal_at = row.terminal_at or timezone.now()
    row.reason_code = reason
    row.save(update_fields=["state", "active", "lease_until", "terminal_at", "reason_code"])
    if row.trigger_id is not None:
        row.trigger.ai_turn_state = AiTurnState.FAILED if reason else AiTurnState.DONE
        row.trigger.save(update_fields=["ai_turn_state"])
    schedule(context, row.conversation_id)


def cancel(row, context, reason):
    """Cancel never rewrites a saved terminal result or its receipt."""
    if row.state not in FINAL:
        row.cancel_pending = bool(row.attempts)
        row.save(update_fields=["cancel_pending"])
        finish(row, context, reason=reason, cancelled=True)


def head(conversation_id):
    return ExternalAgentRequest.objects.select_for_update(of=("self",)).select_related(
        "session__connection__integration", "session__agent__external_binding", "conversation", "trigger",
    ).filter(conversation_id=conversation_id).exclude(state__in=FINAL).order_by("sequence").first()
