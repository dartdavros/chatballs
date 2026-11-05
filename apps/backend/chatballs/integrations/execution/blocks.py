"""Local block transitions. No network, sleep, or external effect handlers."""

from copy import deepcopy

from chatballs.integrations.execution.block_values import actual, error_data
from chatballs.integrations.execution.budgets import MAX_ITEMS
from chatballs.integrations.execution.conditions import evaluate_conditions
from chatballs.integrations.execution.frames import DONE, child, create, save, sequence
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenarios.values import resolve_value


def step_sequence(tenant, run, frame, registry):
    data = frame.definition
    index, steps = data["index"], data["steps"]
    if index == len(steps):
        save(frame, data, "completed")
        return True
    block = steps[index]
    row = child(run, frame, block["id"])
    if row is None:
        create(run, f"{frame.path}/{block['id']}", block["kind"], data["values"],
               parent=frame.path, block=block, number=index + 1)
        return True
    if row.state == "unknown":
        if frame.state == "unknown":
            return False
        save(frame, data, "unknown")
        return True
    if row.state not in DONE:
        return False
    if row.state in {"failed", "cancelled"} and block.get("onError", "stop") != "continue":
        data["error"] = error_data(run, row)
        save(frame, data, row.state, row.error_code)
        return True
    values = data["values"]
    values["states"][block["id"]] = "failed" if row.state == "failed" else "completed"
    result = row.definition
    if "result" in result:
        values["steps"][block["id"]] = result["result"]
    if "event" in result:
        values["event"] = result["event"]
    data["index"] += 1
    save(frame, data, "queued")
    return True


def branch(tenant, run, frame, registry):
    data, block = frame.definition, frame.definition["block"]
    if "selected" not in data:
        condition = {"conditions": block["condition"]}
        matched = evaluate_conditions(condition, run.conversation, run.definition["parameters"],
            registry=registry, values=actual(tenant, run, data["values"]))
        data["selected"] = "then" if matched else "else"
        save(frame, data, "pending")
    row = child(run, frame, data["selected"])
    if row is None:
        sequence(run, frame, data["selected"], block[data["selected"]], data["values"])
        return True
    return copy_outcome(run, frame, row)


def copy_outcome(run, frame, row):
    if row.state not in DONE | {"unknown"} or frame.state == row.state:
        return False
    data = frame.definition
    if row.state == "failed":
        data["error"] = error_data(run, row)
    save(frame, data, row.state, row.error_code)
    return True


def attempt(tenant, run, frame, registry):
    data, block = frame.definition, frame.definition["block"]
    body = child(run, frame, "body")
    if body is None:
        sequence(run, frame, "body", block["body"], data["values"])
        return True
    if body.state != "failed":
        return copy_outcome(run, frame, body)
    catch = child(run, frame, "catch")
    if catch is None:
        values = deepcopy(data["values"])
        values["errors"][block["id"]] = error_data(run, body)
        sequence(run, frame, "catch", block["catch"], values)
        return True
    if catch.state == "completed" and block.get("after", "continue") == "fail":
        data["error"] = error_data(run, body)
        save(frame, data, "failed", body.error_code)
        return True
    return copy_outcome(run, frame, catch)


def fanout(tenant, run, frame, registry):
    data, block = frame.definition, frame.definition["block"]
    loop = block["kind"] == "foreach"
    if "count" not in data:
        items = resolve_value(block["list"], actual(tenant, run, data["values"]), registry) if loop else block["branches"]
        if not isinstance(items, list):
            raise ExecutionDenied("arguments")
        if len(items) > MAX_ITEMS:
            raise ExecutionDenied("budget_iterations")
        from chatballs.integrations.execution.budgets import check_data, reserve
        reserve(run, len(items))
        data.update(count=len(items), items=items if loop else [], next=0)
        check_data(run, data)
        save(frame, data, "pending")
    rows = list(run.progress.filter(parent_path=frame.path).order_by("pk"))
    active = sum(row.state not in DONE for row in rows)
    failures = [row for row in rows if row.state == "failed"]
    unknown = any(row.state == "unknown" for row in rows)
    stop = failures and block.get("onError", "continue" if loop else "wait") == "stop"
    if stop:
        prefix = frame.path + "/"
        pending = run.steps.filter(path__startswith=prefix, sent_at__isnull=True).exclude(state__in=DONE)
        pending.update(state="cancelled", error_code="dependency_failed")
        sent = run.steps.filter(path__startswith=prefix, sent_at__isnull=False).exclude(state__in=DONE).values("path")
        run.progress.filter(path__startswith=prefix).exclude(state__in=DONE).exclude(path__in=sent).update(
            state="cancelled", error_code="dependency_failed")
        rows = list(run.progress.filter(parent_path=frame.path).order_by("pk"))
        active = sum(row.state not in DONE for row in rows)
    limit = block.get("concurrency", 1) if loop else 5
    if not stop and data["next"] < data["count"] and active < limit:
        index = data["next"]
        values = deepcopy(data["values"])
        if loop:
            values["items"][block["id"]] = data["items"][index]
        sequence(run, frame, f"{'iteration' if loop else 'branch'}/{index}",
                 block["body"] if loop else block["branches"][index], values)
        data["next"] += 1
        save(frame, data, "queued")
        return True
    if active:
        if unknown and frame.state != "unknown":
            save(frame, data, "unknown")
            return True
        return False
    if data["next"] < data["count"] and not stop:
        return False
    entries = []
    for index, row in enumerate(rows):
        saved = row.definition
        local = {block["id"] for block in saved["steps"]}
        entries.append({"index": index + 1, "state": row.state,
            "steps": {key: value for key, value in saved["values"]["steps"].items() if key in local},
            "error": error_data(run, row) if row.state in {"failed", "cancelled"} else None})
    if stop:
        entries.extend({"index": i + 1, "state": "cancelled", "steps": {}, "error": {
            "reason": "dependency_failed", "step": block.get("name") or block["id"], "number": i + 1,
            "service": "", "run": str(run.pk)}} for i in range(data["next"], data["count"]))
    data["result"] = {"items": entries, "errors": [entry for entry in entries if entry["state"] != "completed"]} if loop else {
        "branches": {str(i): entry for i, entry in enumerate(entries)}}
    failed = bool(failures) and block.get("onError", "continue" if loop else "wait") != "continue"
    if failed:
        data["error"] = error_data(run, failures[0])
    save(frame, data, "failed" if failed else "completed", failures[0].error_code if failed else "")
    return True
