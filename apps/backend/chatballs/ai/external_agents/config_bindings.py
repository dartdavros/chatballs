"""Per-agent explicit bindings and execution selection, sharing organization admission."""

from django.http import Http404

from chatballs.ai.external_agents.config import audit, require_enabled
from chatballs.ai.external_agents.config_access import (
    binding_payload,
    connection_for,
    owner,
)
from chatballs.ai.external_agents.config_models import ExternalAgentBinding
from chatballs.ai.external_agents.config_policy import (
    POLICY_FIELDS,
    invalid,
    policy_values,
)
from chatballs.ai.external_agents.readiness import ready
from chatballs.ai.models import AIAgent
from chatballs.tenancy.database import tenant_atomic


def agent_for(context, agent_id):
    agent = AIAgent.objects.select_for_update().filter(
        pk=agent_id, organization_id=context.organization_id).first()
    if agent is None:
        raise Http404
    return agent


def save_binding(context, connection_id, agent_id, body):
    if not isinstance(body, dict) or set(body) - ({"externalAgentId"} | set(POLICY_FIELDS)):
        invalid()
    with tenant_atomic(context):
        organization = owner(context)
        require_enabled(organization)
        connection = connection_for(context, connection_id, lock=True)
        agent = agent_for(context, agent_id)
        if not connection.checked_at or not connection.capabilities or not connection.enabled:
            invalid()
        previous = ExternalAgentBinding.objects.select_for_update().filter(agent=agent).first()
        external_id = body.get("externalAgentId", previous.external_agent_id if previous else "")
        if not isinstance(external_id, str) or not external_id.strip() or len(external_id) > 255:
            invalid()
        # New assignment never inherits grants from the previous executor.
        same = previous and previous.enabled and previous.connection_id == connection.pk and previous.external_agent_id == external_id.strip()
        values = policy_values(context, body, previous if same else None)
        binding, _ = ExternalAgentBinding.objects.update_or_create(
            agent=agent, defaults={"organization": organization, "connection": connection,
                                  "external_agent_id": external_id.strip(), "enabled": True, **values},
        )
        if body.get("policyAccepted") is True:
            from chatballs.ai.external_agents.grant_definitions import definitions

            binding.accepted_definitions = definitions(binding)
            binding.save(update_fields=["accepted_definitions"])
        binding.refresh_from_db()
        audit(context, organization, "external.binding_updated", binding.pk)
        return {"binding": binding_payload(binding)}


def remove_binding(context, connection_id, agent_id):
    with tenant_atomic(context):
        organization = owner(context)
        connection = connection_for(context, connection_id, lock=True)
        agent = agent_for(context, agent_id)
        binding = ExternalAgentBinding.objects.filter(connection=connection, agent=agent).first()
        if binding is None:
            raise Http404
        binding.enabled, binding.policy_accepted = False, False
        binding.save(update_fields=["enabled", "policy_accepted"])
        audit(context, organization, "external.binding_removed", binding.pk)
    return {}


def select_execution(context, agent_id, mode):
    if mode not in ("builtin", "external"):
        invalid()
    with tenant_atomic(context):
        organization = owner(context)
        agent = agent_for(context, agent_id)
        if mode == "external":
            require_enabled(organization)
            agent.execution_mode = mode
            if not ready(agent, organization):
                invalid()
        if agent.execution_mode != mode or mode == "external":
            agent.execution_mode = mode
            agent.save(update_fields=["execution_mode"])
            agent.refresh_from_db(fields=["execution_mode", "execution_version"])
        return agent
