"""Secret-free readiness for the agent card, without network or configuration writes."""

from copy import copy

from django.core.exceptions import ObjectDoesNotExist

from chatballs.ai.external_agents.readiness import ready


def execution_projection(agent, organization):
    try:
        binding = agent.external_binding
        connection = binding.connection
        integration = connection.integration
    except ObjectDoesNotExist:
        return {"available": False, "connectionId": None, "name": "", "reason": "notReady"}
    candidate = copy(agent)
    candidate.execution_mode = "external"
    available = ready(candidate, organization)
    if not organization.external_execution_enabled:
        reason = "disabled"
    elif not connection.enabled or not integration.is_active:
        reason = "connectionDisabled"
    elif integration.last_error_code == "incompatible":
        reason = "incompatible"
    elif integration.last_error_code in {"unavailable", "access"}:
        reason = "unavailable" if integration.last_error_code == "unavailable" else "permission"
    elif not connection.checked_at or not connection.capabilities or not connection.inbound_key_hash:
        reason = "notReady"
    elif not available:
        reason = "permission"
    else:
        reason = None
    return {"available": available, "connectionId": connection.pk, "name": integration.name, "reason": reason}
