"""Small persistent frames. Caller holds the root/run lock."""

from copy import deepcopy

from chatballs.integrations.execution.budgets import account_data, reserve, size
from chatballs.integrations.scenario_state.progress import ScenarioProgress

DONE = frozenset({"completed", "failed", "cancelled"})


def create(run, path, kind, values, *, parent="", **data):
    if len(path) > 512:
        from chatballs.integrations.execution.permissions import ExecutionDenied
        raise ExecutionDenied("budget_depth")
    existing = run.progress.filter(path=path).first()
    if existing:
        return existing
    reserve(run)
    payload = {"values": deepcopy(values), **data}
    payload_bytes = size(payload)
    account_data(run, payload_bytes)
    row = ScenarioProgress(organization_id=run.organization_id, run=run, path=path,
                           parent_path=parent, kind=kind, payload_bytes=payload_bytes)
    row.definition = payload
    row.save()
    return row


def save(frame, data, state=None, code=""):
    payload_bytes = size(data)
    account_data(frame.run, payload_bytes - frame.payload_bytes)
    frame.payload_bytes = payload_bytes
    frame.definition = data
    if state:
        frame.state = state
    frame.error_code = code
    frame.save(update_fields=["content", "state", "error_code", "payload_bytes"])
    if frame.parent_path:
        ScenarioProgress.objects.filter(run_id=frame.run_id, path=frame.parent_path).exclude(
            state__in=DONE).update(state="queued")


def child(run, frame, suffix):
    return run.progress.filter(path=f"{frame.path}/{suffix}").first()


def sequence(run, frame, suffix, steps, values):
    return create(run, f"{frame.path}/{suffix}", "sequence", values, parent=frame.path, steps=steps, index=0)
