"""Recheck used action runs before storing and delivering an autonomous reply."""

from chatballs.integrations.execution.ai_policy import authorize_ai
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.runs import ScenarioRun


def allowed(tenant, conversation_id, run_ids):
    for public_id in set(run_ids):
        run = ScenarioRun.objects.filter(organization_id=tenant.organization_id,
            public_id=public_id, conversation_id=conversation_id).first()
        if run is None or run.data_cleared_at or not run.definition.get("ai"):
            return False
        try:
            authorize_ai(tenant, run)
        except ExecutionDenied:
            return False
    return True
