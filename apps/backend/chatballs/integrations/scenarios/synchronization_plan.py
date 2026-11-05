"""Pure directed field decisions; never infer an inverse status mapping."""

from copy import deepcopy
from datetime import datetime

from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenarios.values import RunValues, resolve_value

MISSING = object()


def read(value, path):
    for name in path.split("."):
        if not isinstance(value, dict) or name not in value:
            return MISSING
        value = value[name]
    return value


def put(value, path, item):
    names = path.split(".")
    for name in names[:-1]:
        value = value.setdefault(name, {})
    value[names[-1]] = deepcopy(item)


def converted(mapping, source, *, registry=None):
    if "values" in mapping:
        return next((row["to"] for row in mapping["values"] if type(row["from"]) is type(source) and row["from"] == source), MISSING)
    binding = {"source": "constant", "value": source}
    if mapping.get("transform"):
        binding.update(transform=mapping["transform"], args=mapping.get("args", {}))
    return resolve_value(binding, RunValues(), registry or default_registry())


def plan(pair, left, right, *, baseline=None, choices=None, registry=None):
    baseline, choices = baseline or {}, choices or {}
    result = {"left": {}, "right": {}, "conflicts": [], "delete": "", "unlink": False}
    if left["deleted"] or right["deleted"]:
        policy = pair["deletion"]
        result["unlink"] = policy == "unlink"
        if policy == "propagate" and left["deleted"] != right["deleted"]:
            result["delete"] = "right" if left["deleted"] else "left"
        return result
    fields = {}
    for index, mapping in enumerate(pair["fields"]):
        # Both directed mappings of the same field share one human choice.
        fields.setdefault((mapping["left"], mapping["right"]), str(index))
    for mapping in pair["fields"]:
        identity = fields[(mapping["left"], mapping["right"])]
        direction = mapping["direction"]
        if pair["direction"] not in {"both", direction}:
            continue
        source_side, target_side = ("left", "right") if direction == "forward" else ("right", "left")
        source, target = (left, right) if direction == "forward" else (right, left)
        source_path, target_path = mapping[source_side], mapping[target_side]
        raw = read(source["values"], source_path)
        if raw is MISSING:
            continue
        value = converted(mapping, raw, registry=registry)
        if value is MISSING or value is None and "values" in mapping:
            continue
        current = read(target["values"], target_path)
        if current is not MISSING and value == current:
            continue
        old_source = read(baseline.get(source_side, {}).get("values", {}), source_path)
        old_target = read(baseline.get(target_side, {}).get("values", {}), target_path)
        source_changed, target_changed = raw != old_source, current != old_target
        if not source_changed and not target_changed:
            continue
        conflict = source_changed and target_changed
        choice = choices.get(identity)
        if choice is not None:
            if choice == target_side:
                continue
        elif conflict and pair["conflict"] == "manual":
            if any(item["id"] == identity for item in result["conflicts"]):
                continue
            result["conflicts"].append({"id": identity, "leftField": mapping["left"], "rightField": mapping["right"],
                "left": None if read(left["values"], mapping["left"]) is MISSING else read(left["values"], mapping["left"]),
                "right": None if read(right["values"], mapping["right"]) is MISSING else read(right["values"], mapping["right"]),
                "leftAt": left["modifiedAt"], "rightAt": right["modifiedAt"]})
            continue
        elif conflict and pair["conflict"] == "latest" or pair["sourceOfTruth"] == "latest":
            if source["modifiedAt"] is None or target["modifiedAt"] is None:
                raise ExecutionDenied("conditions_unavailable")
            if datetime.fromisoformat(source["modifiedAt"]) <= datetime.fromisoformat(target["modifiedAt"]):
                continue
        elif pair["sourceOfTruth"] != source_side:
            continue
        put(result[target_side], target_path, value)
    return result
