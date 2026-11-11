"""Read-only operation metadata follows the same current manual permission."""

from chatballs.integrations.execution.actions import resolve_action
from chatballs.integrations.execution.permissions import ExecutionDenied, authorize, direct_policy
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition


def metadata_action(tenant, *, connection_id, operation_key, conversation_id, scenario_id=None):
    if scenario_id:
        scenario = ScenarioDefinition.objects.get(public_id=scenario_id, organization_id=tenant.organization_id)
        document = scenario.definition
        tenant, conversation = authorize(tenant, document, conversation_id, scenario_id=scenario.pk)
        from chatballs.integrations.execution.manual_eligibility import ManualEligibility
        ManualEligibility(tenant, conversation).scenario(scenario)
        from chatballs.integrations.execution.snapshots import walk
        if not any(str(block.get("connection")) == str(connection_id) and block.get("target") == f"service:{operation_key}"
                   for block in walk(document["steps"])):
            raise ExecutionDenied("permission")
    else:
        tenant, _document, _grant, _conversation = direct_policy(tenant, connection_id, operation_key, conversation_id)
    return resolve_action(tenant.organization_id, connection_id, f"service:{operation_key}")


def lookup_keys(spec):
    found = {spec.lookup} if spec.lookup else set()
    for _name, child in spec.properties:
        found |= lookup_keys(child)
    if spec.items:
        found |= lookup_keys(spec.items)
    return found
