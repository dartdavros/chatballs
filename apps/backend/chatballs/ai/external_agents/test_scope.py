"""Runtime authority and route for the initiator's private product test."""

from rest_framework.exceptions import PermissionDenied

from chatballs.ai.external_agents.payloads import open_payload
from chatballs.ai.external_agents.readiness import ready
from chatballs.ai.external_agents.test_models import ExternalAgentTestSession
from chatballs.identity.models import OrganizationMembership

# Runtime helpers are exercised by the dedicated test_test_scope suite.
__test__ = False


def active_scope(conversation, agent, *, require_control=True):
    scope = ExternalAgentTestSession.objects.filter(
        conversation=conversation, agent=agent, organization_id=conversation.organization_id,
        closed_at__isnull=True,
    ).first()
    if (scope is None or not ready(agent, conversation.organization)
            or conversation.lifecycle != "OPEN" or require_control and conversation.control_mode != "AI"
            or not OrganizationMembership.objects.filter(
                user_id=scope.owner_id, user__is_active=True, organization_id=scope.organization_id,
                role__in=["OWNER", "ADMIN"], blocked_at__isnull=True,
            ).exists()):
        raise PermissionDenied(code="control_changed")
    if open_payload(scope.context_ciphertext).get("versions") != policy_versions(agent):
        raise PermissionDenied(code="control_changed")
    return scope


def policy_versions(agent):
    from chatballs.ai.external_agents.custom_field_revisions import fingerprint

    binding, organization = agent.external_binding, agent.organization
    connection = binding.connection
    return {"feature": organization.external_execution_version, "operation": organization.operation_mode_version,
            "execution": agent.execution_version, "lifecycle": agent.lifecycle_version,
            "binding": binding.revision, "policy": binding.policy_version,
            "configuration": connection.revision, "credential": connection.credential_version,
            "integration": connection.integration.runtime_revision, "definitions": fingerprint(binding)}


def test_route(conversation):
    return {"testScope": str(conversation.external_test_scope.public_id),
            "connectionId": None, "transportVersion": None,
            "chatId": "", "representation": "html"}
