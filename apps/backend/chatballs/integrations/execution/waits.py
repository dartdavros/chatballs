"""Persistent registrations: deadline, receipt and employee decision race once."""

from django.utils import timezone

from chatballs.integrations.execution.block_values import actual
from chatballs.integrations.execution.events import schedule
from chatballs.integrations.execution.frames import save
from chatballs.integrations.execution.wait_clock import due_at
from chatballs.integrations.scenario_state.waits import ScenarioWait


def wait(tenant, run, frame, registry):
    data, block = frame.definition, frame.definition["block"]
    row = run.waits.filter(path=frame.path).first()
    if row is None:
        deadline = due_at(block, actual(tenant, run, data["values"]), registry)
        row = ScenarioWait(organization_id=run.organization_id, run=run, path=frame.path,
            kind=block["mode"], integration_id=int(block["connection"]) if str(block.get("connection", "")).isdecimal() else None,
            event_key="conversation.reply" if block["mode"] == "reply" else block.get("event", ""), deadline=deadline)
        row.definition = {"block": block, "values": data["values"]}
        row.save()
        schedule(tenant, run, at=deadline)
        save(frame, data, "pending")
        from chatballs.integrations.automation_events.callbacks import match_wait
        match_wait(tenant, row, registry=registry)
        return True
    if row.state == "pending" and row.deadline and row.deadline <= timezone.now():
        row.state = "completed" if row.kind in {"duration", "until", "clock"} else "expired"
        row.save(update_fields=["state"])
    if row.state == "pending":
        from chatballs.integrations.automation_events.callbacks import match_wait
        match_wait(tenant, row, registry=registry)
        if row.state == "pending":
            return False
    if row.state == "completed" and row.receipt_id:
        data["event"] = row.receipt.definition["payload"]
        data["result"] = {"event": data["event"]}
    stop = row.state == "rejected" or row.state == "expired" and block.get("onTimeout", "continue") == "end"
    save(frame, data, "cancelled" if stop else "completed")
    return True


def pending_operation(tenant, run, step, result):
    from chatballs.integrations.automation_events.ingress import digest
    row = run.waits.filter(path=step.path).first()
    if row:
        return row
    row = ScenarioWait(organization_id=run.organization_id, run=run, path=step.path,
        integration=step.integration, kind="operation", event_key=result.event_key,
        correlation_hash=digest(result.correlation), deadline=result.deadline)
    row.definition = {"effect": str(step.effect_key)}
    row.save()
    schedule(tenant, run, at=row.deadline)
    from chatballs.integrations.automation_events.callbacks import match_wait
    match_wait(tenant, row)
    return row

def expire_operations(tenant, run):
    from chatballs.integrations.execution.checkpoints import finish
    for row in run.waits.select_for_update().filter(kind="operation", state="pending", deadline__lte=timezone.now()):
        step = run.steps.select_for_update().get(path=row.path)
        if step.state == "waiting":
            finish(run, step, "unknown", code="outcome_unavailable")
        row.state = "expired"
        row.save(update_fields=["state"])
