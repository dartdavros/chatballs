"""Declarative links/mapping, without performing links or synchronization."""

from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.adapters.schema import validate_value
from chatballs.integrations.scenarios.bindings import transformed_type
from chatballs.integrations.scenarios.definition import Issue
from chatballs.integrations.scenarios.types import at_path, compatible


def check_synchronization(pairs, *, context, issues, path="synchronization", registry=None):
    if not isinstance(pairs, list) or len(pairs) > 100:
        issues.append(Issue(path, "structure"))
        return
    identifiers = set()
    for i, pair in enumerate(pairs):
        at = f"{path}.{i}"
        fields = {"id", "enabled", "left", "right", "direction", "fields", "sourceOfTruth", "conflict", "deletion", "causality"}
        if not isinstance(pair, dict) or set(pair) != fields:
            issues.append(Issue(at, "structure"))
            continue
        identifier = pair["id"]
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            issues.append(Issue(f"{at}.id", "identifier"))
        identifiers.add(str(identifier))
        if not isinstance(pair["enabled"], bool) or pair["direction"] not in {"forward", "reverse", "both"}:
            issues.append(Issue(at, "policy"))
        for side in ("left", "right"):
            endpoint = pair[side]
            if not isinstance(endpoint, dict) or set(endpoint) != {"connection", "entity"}:
                issues.append(Issue(f"{at}.{side}", "structure"))
            elif (str(endpoint["connection"]), endpoint["entity"]) not in context.entities:
                issues.append(Issue(f"{at}.{side}", "reference"))
        for key, choices in {"sourceOfTruth": {"left", "right", "latest"},
                             "conflict": {"source", "latest", "manual"},
                             "deletion": {"unlink", "keep", "propagate"}}.items():
            if pair[key] not in choices:
                issues.append(Issue(f"{at}.{key}", "policy"))
        if (not isinstance(pair["causality"], dict) or set(pair["causality"]) != {"suppressEcho", "requireExplicitLink"}
                or any(v is not True for v in pair["causality"].values())):
            issues.append(Issue(f"{at}.causality", "policy"))
        _fields(pair, at, context, issues, registry)


def _fields(pair, path, context, issues, registry):
    fields = pair["fields"]
    if not isinstance(fields, list):
        issues.append(Issue(f"{path}.fields", "structure"))
        return
    for i, mapping in enumerate(fields):
        at = f"{path}.fields.{i}"
        if not isinstance(mapping, dict) or set(mapping) - {"left", "right", "direction", "values", "transform", "args"}:
            issues.append(Issue(at, "structure"))
            continue
        if any(not isinstance(mapping.get(k), str) or not mapping[k].strip() for k in ("left", "right")):
            issues.append(Issue(at, "required"))
        if mapping.get("direction") not in {"forward", "reverse"}:
            issues.append(Issue(at, "policy"))
        # Each direction is independent. Never infer the inverse status map.
        values = mapping.get("values", [])
        if not isinstance(values, list) or any(not isinstance(v, dict) or set(v) != {"from", "to"} for v in values):
            issues.append(Issue(f"{at}.values", "structure"))
            continue
        endpoints = [pair["left"], pair["right"]]
        if not all(isinstance(e, dict) and set(e) == {"connection", "entity"} for e in endpoints):
            continue
        keys = [(str(e["connection"]), e["entity"]) for e in endpoints]
        schemas = [context.entities.get(key) for key in keys]
        if None in schemas:
            continue
        specs = [at_path(schemas[0], mapping.get("left")), at_path(schemas[1], mapping.get("right"))]
        if any(spec is None for spec in specs):
            issues.append(Issue(at, "reference"))
            continue
        reverse = mapping.get("direction") == "reverse"
        source, target = (specs[1], specs[0]) if reverse else specs
        target_key = keys[0] if reverse else keys[1]
        target_field = mapping.get("left" if reverse else "right", "").split(".")[0]
        if target_field not in context.writable_fields.get(target_key, set()):
            issues.append(Issue(at, "policy"))
        if "values" in mapping:
            if "transform" in mapping or "args" in mapping:
                issues.append(Issue(at, "policy"))
            seen = set()
            for row in values:
                marker = (type(row["from"]).__name__, repr(row["from"]))
                if marker in seen:
                    issues.append(Issue(f"{at}.values", "identifier"))
                seen.add(marker)
                if validate_value(source, row["from"]) or row["to"] is not None and validate_value(target, row["to"]):
                    issues.append(Issue(f"{at}.values", "type"))
        else:
            converted = transformed_type(mapping, source, registry or default_registry())
            if converted is None or not compatible(converted, target):
                issues.append(Issue(at, "type"))
