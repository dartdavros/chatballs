"""Root-wide technical budgets; no branch is silently truncated."""

import json
from time import monotonic

from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.progress import ScenarioBudget
from chatballs.integrations.scenario_state.runs import ScenarioRun

MAX_INSTANCES = 10000
MAX_ITEMS = 1000
MAX_ACTIVE = 5
MAX_DATA = 10 * 1024 * 1024
MAX_SNAPSHOT = 1024 * 1024


def size(value):
    return len(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode())


def lock_run(tenant, public_id=None, *, pk=None):
    run = ScenarioRun.objects.get(
        **({"pk": pk} if pk else {"public_id": public_id}), organization_id=tenant.organization_id)
    from chatballs.webchat.proactive_guards import for_run
    if run.content and (run.definition.get("ai") or for_run(run) is not None):
        # Match organization mode transitions and AI launch/policy updates:
        # organization before run/step/conversation, never the reverse.
        from chatballs.identity.operation_modes import lock_organization
        lock_organization(tenant.organization_id)
    chain = [run.pk]
    parent = run.parent_id
    while parent:
        ancestor = ScenarioRun.objects.get(pk=parent, organization_id=tenant.organization_id)
        chain.append(parent)
        parent = ancestor.parent_id
        if len(chain) > 16:
            raise ExecutionDenied("budget_depth")
    # All interpreter, receipt and effect paths use root -> descendants.
    for identity in reversed(chain):
        locked = ScenarioRun.objects.select_for_update().get(pk=identity)
    return locked


def root_of(run):
    if run.root_id:
        return run.root
    while run.parent_id:
        run = ScenarioRun.objects.get(pk=run.parent_id, organization_id=run.organization_id)
    return run


def reserve(run, count=1):
    root = root_of(run)
    budget, _ = ScenarioBudget.objects.get_or_create(root=root, organization_id=run.organization_id)
    if budget.instances + count > MAX_INSTANCES or budget.active_seconds >= 3600:
        raise ExecutionDenied("budget_execution")
    budget.instances += count
    budget.save(update_fields=["instances"])


def charge(run, started):
    budget = ScenarioBudget.objects.get(root=root_of(run))
    budget.active_seconds += max(0, monotonic() - started)
    budget.save(update_fields=["active_seconds"])


def check_data(run, value):
    budget, _ = ScenarioBudget.objects.get_or_create(root=root_of(run), organization_id=run.organization_id)
    if size(value) + budget.payload_bytes > MAX_DATA:
        raise ExecutionDenied("budget_volume")


def account_data(run, delta):
    budget, _ = ScenarioBudget.objects.get_or_create(root=root_of(run), organization_id=run.organization_id)
    if budget.payload_bytes + delta > MAX_DATA:
        raise ExecutionDenied("budget_volume")
    budget.payload_bytes = max(0, budget.payload_bytes + delta)
    budget.save(update_fields=["payload_bytes"])


def active_effects(run):
    root = root_of(run)
    from django.db.models import Q
    from django.utils import timezone

    from chatballs.integrations.scenario_state.steps import ScenarioStep
    return ScenarioStep.objects.filter(Q(run=root) | Q(run__root=root),
        state__in=("running", "reconciling"), lease_until__gt=timezone.now()).count()


def causal_chain(run):
    values = [run.scenario_key]
    while run.parent_id:
        run = run.parent
        if run.scenario_key in values or len(values) >= 16:
            raise ExecutionDenied("recursion")
        values.append(run.scenario_key)
    inherited = run.definition.get("causalChain", [])
    result = [*inherited, *reversed(values)]
    if len(result) > 16 or len(set(result)) != len(result):
        raise ExecutionDenied("recursion")
    return tuple(result)
