"""Server-owned automatic principal, rechecked at launch and every effect."""

from chatballs.identity.models import EmployeeRole
from chatballs.integrations.execution.permissions import ExecutionDenied, current_actor
from chatballs.integrations.scenario_state.automation import ScenarioAutomation
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic

KINDS = frozenset({"chatballs", "service", "schedule", "api"})


def delegate(tenant, scenario_id, *, expected=None):
    row = ScenarioAutomation.objects.select_related("delegate__user", "delegate__organization").filter(
        scenario_id=scenario_id, organization_id=tenant.organization_id).first()
    if row is None or row.delegate_id is None or expected is not None and row.delegate_id != expected:
        raise ExecutionDenied("permission")
    actor = current_actor(TenantContext.for_membership(row.delegate))
    if actor.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
        raise ExecutionDenied("permission")
    return actor


def launch_automatic(tenant, scenario, trigger, *, key, parameters=None, event=None, conversation_id=None, registry=None, causal_chain=()):
    from chatballs.integrations.execution.launch import launch
    with tenant_atomic(tenant):
        actor = delegate(tenant, scenario.pk)
        if str(scenario.public_id) in causal_chain or len(causal_chain) >= 16:
            raise ExecutionDenied("recursion")
        return launch(tenant=actor, scenario_id=scenario.public_id, trigger_key=key,
            parameters=parameters or {}, conversation_id=conversation_id, registry=registry,
            automatic={"trigger": trigger, "event": event or {}, "causalChain": list(causal_chain)})


def check(tenant, document, scenario_id, trigger, *, current=False):
    present = any(t["id"] == trigger["id"] and t["kind"] == trigger["kind"] for t in document["triggers"]) if current else trigger in document["triggers"]
    if trigger.get("kind") not in KINDS or not present or not document["access"]["delegated"]:
        raise ExecutionDenied("permission")
    delegate(tenant, scenario_id, expected=tenant.membership_id)


def confirmation_required(operation, run):
    from chatballs.integrations.adapters.contracts import READ_EFFECTS
    data = run.definition
    return data["document"]["access"]["confirm"] == "always" or (
        operation.effect not in READ_EFFECTS and data.get("triggerKind", "staff") not in KINDS | {"synchronization"})
