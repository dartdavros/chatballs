"""Typed conditions shared by scenario guards, branches and event waits."""

from chatballs.integrations.scenarios.bindings import binding_type, check_binding, transformed_type
from chatballs.integrations.scenarios.definition import Issue

OPERATORS = frozenset({"eq", "ne", "gt", "gte", "lt", "lte", "contains", "empty", "filled"})


def check_conditions(group, *, scope, context, registry, path, issues):
    if not isinstance(group, dict) or set(group) != {"mode", "items"} or group["mode"] not in {"all", "any"}:
        issues.append(Issue(path, "structure"))
        return
    if not isinstance(group["items"], list) or len(group["items"]) > 100:
        issues.append(Issue(path, "structure"))
        return
    for i, condition in enumerate(group["items"]):
        at = f"{path}.items.{i}"
        if isinstance(condition, dict) and condition.get("kind") in {"tag", "channel"}:
            key, allowed = ("tag", context.labels) if condition["kind"] == "tag" else ("connection", context.channels)
            fields = {"kind", key, "present"} | ({"scope"} if key == "tag" else set())
            if set(condition) != fields or type(condition.get(key)) is not int or condition[key] not in allowed or type(condition.get("present")) is not bool:
                issues.append(Issue(at, "reference"))
            if key == "tag" and condition.get("scope") not in {"contact", "conversation"}:
                issues.append(Issue(at, "condition"))
            continue
        if isinstance(condition, dict) and condition.get("kind") in {"context_present", "no_link", "has_link"}:
            kind = condition["kind"]
            if kind == "context_present":
                from chatballs.integrations.scenarios.types import at_path
                if set(condition) - {"kind", "path", "present"} or at_path(context.context, condition.get("path")) is None or type(condition.get("present", True)) is not bool:
                    issues.append(Issue(at, "reference"))
            elif (set(condition) != {"kind", "entity", "connection"}
                  or str(condition.get("connection")) not in context.connections
                  or (str(condition.get("connection")), condition.get("entity")) not in context.entities):
                issues.append(Issue(at, "reference"))
            continue
        if not isinstance(condition, dict) or set(condition) - {"left", "op", "right"}:
            issues.append(Issue(at, "condition"))
            continue
        left = condition.get("left")
        op = condition.get("op")
        spec = binding_type(left, scope, context) if isinstance(left, dict) else None
        if spec is not None:
            spec = transformed_type(left, spec, registry)
        if spec is None or op not in OPERATORS:
            issues.append(Issue(at, "condition"))
            continue
        check_binding(left, spec, scope=scope, context=context, registry=registry, path=f"{at}.left", issues=issues)
        if op in {"gt", "gte", "lt", "lte"} and spec.type not in {"number", "integer", "date", "datetime"}:
            issues.append(Issue(at, "type"))
        if op == "contains" and spec.type not in {"string", "array"}:
            issues.append(Issue(at, "type"))
        if op not in {"empty", "filled"}:
            target = spec.items if op == "contains" and spec.type == "array" else spec
            if target:
                check_binding(condition.get("right"), target, scope=scope, context=context, registry=registry,
                              path=f"{at}.right", issues=issues)
