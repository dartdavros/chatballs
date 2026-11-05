"""Request-scoped native catalog filtering; execution always reauthorizes."""

from dataclasses import replace

from chatballs.i18n import t
from chatballs.identity.models import EmployeeRole
from chatballs.identity.policy import capabilities_in_any_scope
from chatballs.integrations.action_catalog.registry import native_actions
from chatballs.integrations.service_connections.payloads import field_payload


def manual_actions(tenant, grants, conversation):
    # The caller has already resolved the current actor and checked visibility
    # of the selected conversation. Do not repeat those same database queries
    # once per descriptor. These are presentation choices, never effect grants.
    manager = tenant.membership.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}
    if conversation is not None and conversation.archived_at is not None:
        return []
    allowed = {row.native_key: row for row in grants if row.integration_id is None}
    capabilities = capabilities_in_any_scope(tenant.membership)
    items = []
    for action in native_actions():
        if action.capability and action.capability not in capabilities:
            continue
        grant = allowed.get(action.key)
        if grant and action.scope == "organization" and grant.scope != "organization":
            continue
        if not manager and grant is None:
            continue
        if not manager and grant.scope != "organization" and conversation is None:
            continue
        if not manager and grant.scope == "contact" and not conversation.contact_id:
            continue
        parameters = action.operation.input
        if conversation is not None:
            parameters = replace(parameters, properties=tuple((name, field)
                for name, field in parameters.properties
                if name != "conversation_id" or not field.required))
        items.append({"id": f"chatballs:{action.key}", "kind": "operation",
            "title": t(action.operation.title_key), "available": True, "reason": "",
            "connectionId": "chatballs", "operationKey": action.key, "connection": "",
            "parameters": field_payload("", parameters)})
    return items
