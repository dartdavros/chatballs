"""Resolve actual typed inputs before a caller may perform an effect.

This module has no action handlers, I/O or credentials. Execution tasks must
apply their principal/policy checks and call this boundary before each effect.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.adapters.schema import TypeSpec, validate_value
from chatballs.integrations.scenarios.definition import Issue


@dataclass
class RunValues:
    parameters: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    event: dict = field(default_factory=dict)
    steps: dict = field(default_factory=dict)
    items: dict = field(default_factory=dict)
    errors: dict = field(default_factory=dict)
    files: set[str] = field(default_factory=set)
    states: dict = field(default_factory=dict)


class InvalidValues(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__("invalid_scenario_values")


def _path(value, path):
    for part in path.split(".") if path else ():
        if isinstance(value, dict):
            if part not in value:
                raise KeyError(part)
            value = value[part]
        elif isinstance(value, list) and part.isdecimal():
            value = value[int(part)]
        else:
            raise KeyError(part)
    return value


def resolve_value(value: Any, actual: RunValues, registry=None):
    registry = registry or default_registry()
    if isinstance(value, list):
        return [resolve_value(child, actual, registry) for child in value]
    if not isinstance(value, dict):
        raise ValueError("binding")
    source = value.get("source")
    if not isinstance(source, str):
        return {name: resolve_value(child, actual, registry) for name, child in value.items()}
    if source == "constant":
        result = deepcopy(value["value"])
    elif "aspect" in value:
        if source != "step" or value["aspect"] != "state" or value.get("path"):
            raise ValueError("binding")
        result = actual.states[value["step"]]
    elif source in {"parameter", "input"}:
        result = _path(actual.parameters[value["name"]], value.get("path", ""))
    else:
        roots = {"context": actual.context, "event": actual.event, "step": actual.steps,
                 "item": actual.items, "error": actual.errors}
        root = roots[source]
        if source in {"step", "item", "error"}:
            root = root[value["step"]]
        result = _path(root, value.get("path", ""))
    if "transform" in value:
        extension = registry.extension("transform", value["transform"])
        if extension is None or validate_value(extension.implementation.arguments, value.get("args", {})):
            raise ValueError("transform")
        result = extension.implementation.apply(result, **value.get("args", {}))
    return result


def prepare_inputs(schema: TypeSpec, bindings: dict, actual: RunValues, *, registry=None):
    issues = []
    resolved = {}
    for name, binding in bindings.items():
        try:
            resolved[name] = resolve_value(binding, actual, registry)
        except (KeyError, IndexError, TypeError, ValueError, ArithmeticError):
            issues.append(Issue(name, "required"))
    issues += [Issue(issue.path, issue.code) for issue in validate_value(schema, resolved)]

    def files(spec, value, path=""):
        if spec.type == "file" and isinstance(value, dict):
            if str(value.get("fileId")) not in actual.files:
                issues.append(Issue(path, "reference"))
        elif spec.type == "object" and isinstance(value, dict):
            for key, child in spec.properties:
                if key in value:
                    files(child, value[key], f"{path}.{key}" if path else key)
        elif spec.type == "array" and spec.items and isinstance(value, list):
            for index, child in enumerate(value):
                files(spec.items, child, f"{path}.{index}")
    files(schema, resolved)
    if issues:
        raise InvalidValues(issues)
    return resolved
