"""A call path identifies one child Run, including after parent/worker crashes."""

import hashlib

from chatballs.integrations.execution.block_values import actual
from chatballs.integrations.execution.budgets import (
    MAX_SNAPSHOT,
    account_data,
    reserve,
    root_of,
    size,
)
from chatballs.integrations.execution.events import schedule
from chatballs.integrations.execution.frames import save
from chatballs.integrations.execution.permissions import ExecutionDenied, authorize
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenarios.types import read_type
from chatballs.integrations.scenarios.values import prepare_inputs


def call(tenant, run, frame, registry):
    data, block = frame.definition, frame.definition["block"]
    child = run.children.filter(call_path=frame.path).first()
    if child is None:
        saved = run.definition["graph"][str(block["scenario"])]
        document = saved["document"]
        if not any(t["kind"] == "scenario" for t in document["triggers"]) or not document["access"]["delegated"]:
            raise ExecutionDenied("permission")
        if run.definition.get("ai"):
            from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
            current = ScenarioDefinition.objects.get(pk=saved["id"], organization_id=run.organization_id)
            if not current.enabled or not current.definition["access"]["delegated"] or not any(
                t["kind"] == "scenario" for t in current.definition["triggers"]
            ):
                raise ExecutionDenied("permission")
        else:
            authorize(tenant, document, run.conversation_id, scenario_id=saved["id"], trigger_kind="scenario")
        inputs = prepare_inputs(read_type(document["parameters"]), block["inputs"],
                                actual(tenant, run, data["values"]), registry=registry)
        reserve(run)
        child = ScenarioRun(organization_id=run.organization_id, parent=run, root=root_of(run), call_path=frame.path,
            scenario_id=saved["id"], scenario_key=str(block["scenario"]),
            trigger_key=hashlib.sha256(f"{run.public_id}:{frame.path}".encode()).hexdigest(),
            revision=saved["revision"], initiator=run.initiator, conversation_id=run.conversation_id)
        child.definition = {**run.definition, "document": document, "parameters": inputs, "kind": "scenario", "composite": True}
        if size(child.definition) > MAX_SNAPSHOT:
            raise ExecutionDenied("budget_volume")
        child.structure = {"name": saved["name"]}
        account_data(run, size(child.definition))
        child.save()
        # Reserve the child's initial cursor in this same savepoint. Exhaustion
        # fails the call visibly instead of leaving a child unable to start.
        from chatballs.integrations.execution.block_values import initial
        from chatballs.integrations.execution.frames import create
        create(child, "steps", "sequence", initial(child), steps=document["steps"], index=0)
        schedule(tenant, child)
        save(frame, data, "pending")
        return True
    if not child.finished_at and child.state != "unknown":
        return False
    if frame.state == child.state:
        return False
    if child.state == "completed":
        data["result"] = child.progress.get(path="steps").definition["result"]
    save(frame, data, child.state, "child_failed" if child.state == "failed" else "")
    return True
