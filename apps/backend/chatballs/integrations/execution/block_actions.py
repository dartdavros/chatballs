"""Materialize a ready action once; effects still execute in runner.py."""

from django.utils import timezone

from chatballs.integrations.execution.actions import resolve_action
from chatballs.integrations.execution.ai_policy import needs_confirmation
from chatballs.integrations.execution.block_values import actual
from chatballs.integrations.execution.events import journal, schedule
from chatballs.integrations.execution.files import lock_input_files, own_input_files
from chatballs.integrations.execution.frames import save
from chatballs.integrations.execution.snapshots import check_contract
from chatballs.integrations.scenario_state.steps import ScenarioStep
from chatballs.integrations.scenarios.values import prepare_inputs


def action(tenant, run, frame, registry):
    data = frame.definition
    step = run.steps.filter(path=frame.path).first()
    if step:
        if step.state not in {"completed", "failed", "cancelled", "unknown"}:
            return False
        if frame.state == step.state:
            return False
        if step.state == "completed":
            data["result"] = step.definition.get("result", {})
        data["service"] = step.integration.name if step.integration else ""
        save(frame, data, step.state, step.error_code)
        return True
    block = data["block"]
    integration, _, adapter, _, operation = resolve_action(
        run.organization_id, block["connection"], block["target"], registry=registry)
    check_contract(run, block, operation, adapter)
    arguments = prepare_inputs(operation.input, block["inputs"],
                               actual(tenant, run, data["values"]), registry=registry)
    from chatballs.integrations.execution.budgets import account_data, size
    values = {"arguments": arguments, "_responseReservation": operation.limits.max_response_bytes}
    account_data(run, size(values) + operation.limits.max_response_bytes)
    files = lock_input_files(tenant, operation, arguments)
    step = ScenarioStep(organization_id=run.organization_id, run=run, path=frame.path,
        integration=integration, adapter_key=adapter.key, adapter_version=adapter.contract_version,
        operation_key=operation.key, retry_strategy=operation.retry, due_at=timezone.now())
    step.definition = values
    step.state = "approval" if needs_confirmation(run, operation) else "queued"
    step.save()
    own_input_files(step, files)
    save(frame, data, "pending")
    journal(run, "created", step)
    if run.definition.get("ai"):
        from chatballs.integrations.execution.ai_deadlines import schedule_expiry
        schedule_expiry(tenant, run, step)
    if step.state == "queued":
        schedule(tenant, run)
    return True
