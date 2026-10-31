"""Intentional repetition is a new audited command, never recovery in disguise."""

from chatballs.identity.audit import record_audit_event
from chatballs.integrations.execution.launch import launch, launch_direct
from chatballs.integrations.execution.permissions import ExecutionDenied, view_run
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


def intentional_repeat(tenant, public_id, *, trigger_key, acknowledged):
    if acknowledged != str(public_id) or not isinstance(trigger_key, str) or not 1 <= len(trigger_key) <= 100:
        raise ExecutionDenied("repeat_confirmation")
    with tenant_atomic(tenant):
        source = ScenarioRun.objects.select_for_update().get(public_id=public_id, organization_id=tenant.organization_id)
        view_run(tenant, source)
        if source.data_cleared_at or source.state not in {"completed", "failed", "cancelled", "unknown"}:
            raise ExecutionDenied("state_changed")
        key = f"repeat:{public_id}:{trigger_key}"
        if source.definition.get("kind") == "direct":
            step = source.steps.get()
            run, created = launch_direct(tenant=tenant, connection_id=step.integration_id, operation_key=step.operation_key,
                trigger_key=key, arguments=step.definition["arguments"], conversation_id=source.conversation_id)
        else:
            if source.scenario_id is None:
                raise ExecutionDenied("scenario_disabled")
            run, created = launch(tenant=tenant, scenario_id=source.scenario.public_id, trigger_key=key,
                parameters=source.definition["parameters"], conversation_id=source.conversation_id)
        if created:
            record_audit_event(action="integrations.run_intentional_repeat", actor=tenant.actor_user,
                organization=tenant.organization, object_type="ScenarioRun", object_id=str(run.public_id),
                payload={"originalRunId": str(public_id)})
        return run
