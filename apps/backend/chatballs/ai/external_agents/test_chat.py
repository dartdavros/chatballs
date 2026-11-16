"""Initiator-owned test sessions on the native durable external-agent pipeline."""

from django.http import Http404
from django.utils import timezone

from chatballs.ai.external_agents.config_access import owner
from chatballs.ai.external_agents.config_policy import invalid
from chatballs.ai.external_agents.payloads import seal
from chatballs.ai.external_agents.readiness import ready
from chatballs.ai.external_agents.state import FINAL, cancel, enqueue
from chatballs.ai.external_agents.test_context import validate
from chatballs.ai.external_agents.test_models import ExternalAgentTestSession
from chatballs.ai.external_agents.test_projection import project
from chatballs.ai.external_agents.test_scope import policy_versions
from chatballs.ai.models import AIAgent
from chatballs.conversations.models import Conversation, Message
from chatballs.tenancy.database import tenant_atomic


def agent_for(context, channel_id, *, admission=True):
    organization = owner(context)
    agent = AIAgent.objects.select_for_update().filter(
        channel_id=channel_id, organization_id=context.organization_id,
    ).first()
    if agent is None:
        raise Http404
    if admission and not ready(agent, organization):
        invalid()
    return agent


def scope_for(context, channel_id, scope_id, *, admission=False):
    agent = agent_for(context, channel_id, admission=admission)
    scope = ExternalAgentTestSession.objects.select_for_update().filter(
        public_id=scope_id, agent=agent, owner=context.actor_user,
        organization_id=context.organization_id,
    ).select_related("conversation").first()
    if scope is None:
        raise Http404
    return scope


def close_scope(scope, context):
    if scope.closed_at:
        return
    scope.closed_at = timezone.now()
    scope.save(update_fields=["closed_at"])
    for request in scope.conversation.externalagentrequest_set.select_for_update().exclude(state__in=FINAL):
        cancel(request, context, "control_revoked")


def start(context, channel_id, body):
    if not isinstance(body, dict) or set(body) - {"clientData"}:
        invalid()
    with tenant_atomic(context):
        agent = agent_for(context, channel_id)
        data = validate(agent.external_binding, body.get("clientData", {}))
        for scope in ExternalAgentTestSession.objects.select_for_update().filter(
            agent=agent, owner=context.actor_user, closed_at__isnull=True,
        ):
            close_scope(scope, context)
        conversation = Conversation.including_tests.create(
            organization=context.organization, channel=agent.channel, is_test=True,
        )
        scope = ExternalAgentTestSession.objects.create(
            agent=agent, owner=context.actor_user, conversation=conversation,
            context_ciphertext=seal({"values": data, "versions": policy_versions(agent)}),
        )
        return project(scope)


def read(context, channel_id, scope_id):
    with tenant_atomic(context):
        return project(scope_for(context, channel_id, scope_id))


def send(context, channel_id, scope_id, body):
    if not isinstance(body, dict) or set(body) != {"message"} or not isinstance(body["message"], str):
        invalid()
    text = body["message"].strip()
    if not text or len(text) > 10000:
        invalid()
    with tenant_atomic(context):
        scope = scope_for(context, channel_id, scope_id, admission=True)
        if scope.closed_at or scope.conversation.control_mode != "AI":
            invalid()
        message = Message.including_tests.create(conversation=scope.conversation, author_type="CONTACT", text=text)
        enqueue(message, str(context.actor_user.pk), context)
        return project(scope)


def close(context, channel_id, scope_id):
    with tenant_atomic(context):
        close_scope(scope_for(context, channel_id, scope_id), context)
