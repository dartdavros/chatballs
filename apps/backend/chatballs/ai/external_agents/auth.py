"""Scoped Bearer resolves tenant before data; session authority binds monotonic versions."""

import hashlib
import hmac
from contextlib import contextmanager
from uuid import UUID, uuid4

from django.http import Http404
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from chatballs.ai.external_agents.config_models import (
    ExternalAgentBinding,
    ExternalAgentConnection,
)
from chatballs.ai.external_agents.custom_field_revisions import fingerprint
from chatballs.ai.external_agents.readiness import consent_current
from chatballs.ai.external_agents.session_models import ExternalAgentSession
from chatballs.ai.models import AIAgent
from chatballs.conversations.models import Conversation
from chatballs.identity.operation_modes import autonomous_allowed, lock_organization
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import _unique_route
from chatballs.tenancy.lookup import load_organization

OPERATIONS = frozenset({"results", "messages", "handoff", "deliveries", "history",
                        "files.read", "files.write", "reply-templates"})


def key_hash(token):
    return hashlib.sha256(token.encode("ascii")).hexdigest()


@contextmanager
def authenticated(authorization):
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        raise AuthenticationFailed(code="invalid_credentials")
    token = authorization[7:]
    if not 32 <= len(token) <= 256 or not token.isascii():
        raise AuthenticationFailed(code="invalid_credentials")
    hashed = key_hash(token)
    route = _unique_route("external_agent_key_directory", hashed)
    if route is None:
        raise AuthenticationFailed(code="invalid_credentials")
    context = TenantContext.for_resource(load_organization(route.organization_id))
    with tenant_atomic(context):
        organization = lock_organization(context.organization_id)
        connection = ExternalAgentConnection.objects.select_for_update().filter(pk=route.resource_id).first()
        if connection is None or not connection.inbound_key_hash or not hmac.compare_digest(connection.inbound_key_hash, hashed):
            raise AuthenticationFailed(code="invalid_credentials")
        if not organization.external_execution_enabled or not connection.enabled or not connection.integration.is_active:
            raise PermissionDenied(code="permission_denied")
        yield context, connection


def _current(context, connection, agent_id, conversation_id, *, require_control=True):
    organization = lock_organization(context.organization_id)
    connection = ExternalAgentConnection.objects.select_for_update().filter(
        pk=connection.pk, organization_id=context.organization_id).first()
    if connection is None:
        raise Http404
    agent = AIAgent.objects.select_for_update().filter(pk=agent_id, organization=organization).first()
    conversation = Conversation.including_tests.select_for_update(of=("self",)).filter(
        pk=conversation_id, organization=organization).select_related("channel", "connection").first()
    binding = ExternalAgentBinding.objects.filter(agent=agent, connection=connection, enabled=True).first()
    if agent is None or conversation is None or binding is None or conversation.channel_id != agent.channel_id:
        raise Http404
    conversation.channel.ai_agent = agent
    if conversation.is_test:
        from chatballs.ai.external_agents.test_scope import active_scope

        scope = active_scope(conversation, agent, require_control=require_control)
    elif require_control and (not autonomous_allowed(conversation.channel, organization=organization,
                              connection=conversation.connection, conversation=conversation) or not consent_current(conversation)):
        raise PermissionDenied(code="control_changed")
    versions = {
        "organization": organization.pk, "connection": connection.pk, "agent": agent.pk,
        "conversation": conversation.pk, "feature": organization.external_execution_version,
        "operation": organization.operation_mode_version, "execution": agent.execution_version,
        "lifecycle": agent.lifecycle_version, "control": conversation.ai_control_version,
        "assignment": conversation.assignment_version, "configuration": connection.revision,
        "credential": connection.credential_version, "integration": connection.integration.runtime_revision,
        "binding": binding.pk, "bindingVersion": binding.revision, "policy": binding.policy_version,
        "exportPolicy": fingerprint(binding),
        "speech": [agent.transcription_integration_id,
                   agent.transcription_integration.runtime_revision if agent.transcription_integration_id else None,
                   agent.transcription_integration.is_active if agent.transcription_integration_id else None,
                   agent.transcription_integration.status if agent.transcription_integration_id else None,
                   agent.transcription_model, agent.transcription_language],
    }
    if conversation.is_test:
        versions["testScope"] = str(scope.public_id)
    return connection, agent, conversation, binding, versions


def issue_authorization(context, connection, agent_id, conversation_id):
    """Caller holds tenant transaction; admission precedes dispatch/export."""
    connection, agent, conversation, binding, versions = _current(context, connection, agent_id, conversation_id)
    session, _ = ExternalAgentSession.objects.select_for_update().get_or_create(
        connection=connection, agent=agent, conversation=conversation,
        binding_version=binding.revision, execution_version=agent.execution_version,
    )
    if session.authorization_versions != versions:
        session.authorization_id, session.authorization_versions = uuid4(), versions
        session.save(update_fields=["authorization_id", "authorization_versions"])
    return session


def authorize_session(context, connection, *, conversation_id, authorization_id, operation):
    if operation not in OPERATIONS:
        raise PermissionDenied(code="permission_denied")
    try:
        authorization_id = UUID(str(authorization_id))
        if isinstance(conversation_id, bool) or not str(conversation_id).isascii() or not str(conversation_id).isdigit():
            raise ValueError
        conversation_id = int(conversation_id)
        if not 0 < conversation_id < 2**63:
            raise ValueError
    except (ValueError, TypeError, AttributeError) as error:
        raise Http404 from error
    session = ExternalAgentSession.objects.filter(
        organization_id=context.organization_id, connection=connection,
        conversation_id=conversation_id, authorization_id=authorization_id,
    ).first()
    if session is None:
        raise Http404
    _, _, _, binding, versions = _current(context, connection, session.agent_id, conversation_id)
    if session.authorization_versions != versions:
        raise PermissionDenied(code="control_changed")
    if operation == "messages" and not binding.proactive_enabled:
        raise PermissionDenied(code="proactive_disabled")
    return session
