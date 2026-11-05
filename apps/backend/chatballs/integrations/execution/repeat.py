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
        if source.definition.get("kind") == "synchronization":
            import hashlib

            from chatballs.identity.models import EmployeeRole
            from chatballs.integrations.execution.permissions import current_actor
            from chatballs.integrations.scenarios.synchronization_runtime import lock, start_cycle
            if current_actor(tenant).membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
                raise ExecutionDenied("permission")
            digest = hashlib.sha256(key.encode()).hexdigest()
            run = ScenarioRun.objects.filter(organization_id=tenant.organization_id, scenario_key=source.scenario_key, trigger_key=digest).first()
            created = run is None
            if created:
                row = lock(tenant, source.definition["exchange"]["checkpoint"])
                if row.run_id != source.pk:
                    raise ExecutionDenied("state_changed")
                start_cycle(tenant, row, trigger_key=key)
                run = row.run
        elif source.definition.get("triggerKind") in {"chatballs", "service", "schedule", "api"}:
            from chatballs.integrations.execution.automation import launch_automatic
            if source.scenario_id is None:
                raise ExecutionDenied("scenario_disabled")
            old = source.definition["trigger"]
            trigger = next((t for t in source.scenario.definition["triggers"] if t["id"] == old["id"] and t["kind"] == old["kind"]), None)
            if trigger is None:
                raise ExecutionDenied("permission")
            run, created = launch_automatic(tenant, source.scenario, trigger, key=key,
                parameters=source.definition["parameters"], event=source.definition.get("event", {}),
                conversation_id=source.conversation_id, causal_chain=source.definition.get("causalChain", []))
        elif source.definition.get("kind") == "direct":
            step = source.steps.get()
            run, created = launch_direct(tenant=tenant, connection_id=step.integration_id if step.integration_id else "chatballs", operation_key=step.operation_key,
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
