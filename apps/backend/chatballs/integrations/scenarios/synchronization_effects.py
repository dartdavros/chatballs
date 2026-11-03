"""Planning and domain effects commit with their native result receipts."""

from copy import deepcopy
from datetime import timedelta

from django.utils import timezone

from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenarios.synchronization_access import binding_for
from chatballs.integrations.scenarios.synchronization_native import apply, record
from chatballs.integrations.scenarios.synchronization_plan import plan
from chatballs.integrations.scenarios.synchronization_runtime import lock, remote_snapshot


def prepare(tenant, run, row, binding):
    data, command = row.definition, run.definition["exchange"]
    native_side = "left" if command["pair"]["left"]["connection"] == "chatballs" else "right"
    remote_side = "right" if native_side == "left" else "left"
    observed = {native_side: record(tenant, command["link"]), remote_side: remote_snapshot(binding,
        run.steps.get(path="steps/read").definition["result"])}
    resolution = data.get("resolution")
    if resolution and (row.link.revision != resolution["linkRevision"] or any(
            observed[side]["version"] != resolution["versions"][side] for side in ("left", "right"))):
        return OperationResult(ResultState.FAILED, error_code="state_changed")
    result = plan(command["pair"], **observed, baseline=data.get("baseline"),
        choices=resolution["choices"] if resolution else None)
    data["observed"] = observed
    if result["conflicts"]:
        data["conflicts"] = result["conflicts"]
        row.definition, row.state = data, "decision"
        row.save()
        return OperationResult(ResultState.DECISION)
    remote, identifier = observed[remote_side], command["link"]["external_id"]
    causal = f"exchange:{row.pk}:{row.generation}"
    output = {"update": bool(result[remote_side]), "delete": result["delete"] == remote_side,
        "local": bool(result[native_side]) or result["delete"] == native_side,
        "updateArguments": {}, "deleteArguments": {}, "localArguments": {
            "expected": observed[native_side]["version"], "changes": result[native_side], "delete": result["delete"] == native_side}}
    if output["update"]:
        if not binding.update_operation or not binding.update_arguments:
            raise ExecutionDenied("operation_unavailable")
        output["updateArguments"] = binding.update_arguments(identifier, result[remote_side], remote["version"], causal)
    if output["delete"]:
        if not binding.delete_operation or not binding.delete_arguments:
            raise ExecutionDenied("operation_unavailable")
        output["deleteArguments"] = binding.delete_arguments(identifier, remote["version"], causal)
    data["planned"] = result
    row.definition = data
    row.save()
    return output


def merge(target, patch):
    for name, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(name), dict):
            merge(target[name], value)
        else:
            target[name] = deepcopy(value)


def execute(tenant, run, key, arguments):
    if run.definition.get("kind") != "synchronization":
        raise ExecutionDenied("permission")
    command = run.definition["exchange"]
    row = lock(tenant, command["checkpoint"])
    if row.generation != command["generation"] or row.run_id != run.pk:
        raise ExecutionDenied("state_changed")
    _, binding = binding_for(tenant, row.link)
    if key == "synchronization.plan":
        return prepare(tenant, run, row, binding)
    data = row.definition
    native_side = "left" if command["pair"]["left"]["connection"] == "chatballs" else "right"
    remote_side = "right" if native_side == "left" else "left"
    if key == "synchronization.validate":
        remote = remote_snapshot(binding, run.steps.get(path="steps/current").definition["result"])
        native = record(tenant, command["link"])
        if remote["version"] != data["observed"][remote_side]["version"] or native["version"] != data["observed"][native_side]["version"]:
            return OperationResult(ResultState.FAILED, error_code="state_changed")
        return {"valid": True}
    if key == "synchronization.local":
        return apply(tenant, command["link"], arguments["expected"], arguments["changes"], delete=arguments["delete"])
    if key != "synchronization.finish":
        raise ExecutionDenied("operation_unavailable")
    remote = remote_snapshot(binding, run.steps.get(path="steps/verify").definition["result"])
    expected = deepcopy(data["observed"])
    local = run.steps.filter(operation_key="synchronization.local", state="completed").first()
    if local:
        expected[native_side] = local.definition["result"]
    outcome = data["planned"]
    merge(expected[remote_side]["values"], outcome[remote_side])
    if outcome["delete"] == remote_side:
        expected[remote_side]["deleted"] = True
    expected[remote_side]["version"] = remote["version"]
    expected[remote_side]["modifiedAt"] = remote["modifiedAt"]
    if (outcome["unlink"] or all(expected[side]["deleted"] for side in ("left", "right"))) and row.link.revision == command["link"]["revision"]:
        row.link.active, row.link.revision = False, row.link.revision + 1
        row.link.save(update_fields=["active", "revision", "updated_at"])
    data["baseline"] = expected if row.link.revision == command["link"]["revision"] else {}
    for name in ("resolution", "conflicts", "observed", "planned"):
        data.pop(name, None)
    row.definition = data
    row.state, row.error_code = "idle", ""
    row.due_at = timezone.now() + timedelta(seconds=30)
    row.save()
    return {"completed": True}
