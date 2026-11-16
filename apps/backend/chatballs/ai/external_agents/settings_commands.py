"""One atomic settings save; explicit network checks remain a separate operation."""

from chatballs.ai.external_agents import config, config_bindings
from chatballs.ai.external_agents.config_access import connection_for, owner
from chatballs.ai.external_agents.config_policy import invalid
from chatballs.tenancy.database import tenant_atomic


def save_configuration(context, connection_id, body):
    if not isinstance(body, dict) or set(body) != {
        "revision", "bindingRevisions", "connection", "bindings", "removeAgentIds",
    }:
        invalid()
    patch, bindings, removed = body["connection"], body["bindings"], body["removeAgentIds"]
    if (type(body["revision"]) is not int or not isinstance(patch, dict)
            or not isinstance(bindings, list) or not isinstance(removed, list)
            or any(type(identifier) is not int for identifier in removed)):
        invalid()
    identifiers = []
    for binding in bindings:
        if not isinstance(binding, dict) or type(binding.get("agentId")) is not int:
            invalid()
        identifiers.append(binding["agentId"])
    if len(set(identifiers + removed)) != len(identifiers + removed):
        invalid()
    with tenant_atomic(context):
        organization = owner(context)
        config.require_enabled(organization)
        row = connection_for(context, connection_id, lock=True)
        if row.revision != body["revision"]:
            invalid()
        revisions = {str(binding.agent_id): [binding.revision, binding.policy_version]
                     for binding in row.bindings.select_for_update().filter(enabled=True)}
        if body["bindingRevisions"] != revisions:
            invalid()
        for identifier in sorted(removed):
            config_bindings.remove_binding(context, connection_id, identifier)
        for binding in sorted(bindings, key=lambda item: item["agentId"]):
            config_bindings.save_binding(context, connection_id, binding["agentId"],
                                         {key: value for key, value in binding.items() if key != "agentId"})
        if patch:
            config.update_connection(context, connection_id, patch)
        return config.settings(context)
