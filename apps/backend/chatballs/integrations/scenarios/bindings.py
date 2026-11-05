"""Bindings are data references and registered typed transforms, never code."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from chatballs.integrations.adapters.registry import AdapterRegistry
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec, validate_value
from chatballs.integrations.scenarios.definition import DefinitionContext, Issue
from chatballs.integrations.scenarios.types import at_path, compatible

ERROR_TYPE = TypeSpec("object", properties=tuple(
    (key, TypeSpec("string", required=True)) for key in ("reason", "step", "service", "run")
) + (("number", TypeSpec("integer", required=True)),))
STEP_STATE_TYPE = TypeSpec("enum", options=(EnumOption("completed", "scenarios.step_completed"), EnumOption("failed", "scenarios.step_failed")))


@dataclass
class BindingScope:
    parameters: TypeSpec
    event: TypeSpec = field(default_factory=lambda: TypeSpec("object"))
    steps: dict[str, TypeSpec] = field(default_factory=dict)
    items: dict[str, TypeSpec] = field(default_factory=dict)
    errors: set[str] = field(default_factory=set)
    states: set[str] = field(default_factory=set)

    def fork(self) -> BindingScope:
        return BindingScope(self.parameters, self.event, dict(self.steps), dict(self.items), set(self.errors), set(self.states))


def check_binding(value: Any, target: TypeSpec, *, scope: BindingScope, context: DefinitionContext,
                  registry: AdapterRegistry, path: str, issues: list[Issue]) -> None:
    is_binding = isinstance(value, dict) and isinstance(value.get("source"), str)
    if isinstance(value, dict) and not is_binding and target.type == "object":
        fields = dict(target.properties)
        for name, child in fields.items():
            if child.required and name not in value:
                issues.append(Issue(f"{path}.{name}", "required"))
        for name, child in value.items():
            spec = fields.get(name)
            if spec:
                check_binding(child, spec, scope=scope, context=context, registry=registry,
                              path=f"{path}.{name}", issues=issues)
            elif target.open:
                check_untyped(child, scope=scope, context=context, registry=registry,
                              path=f"{path}.{name}", issues=issues)
            else:
                issues.append(Issue(f"{path}.{name}", "unknown"))
        return
    if isinstance(value, list) and target.type == "array" and target.items:
        for i, child in enumerate(value):
            check_binding(child, target.items, scope=scope, context=context, registry=registry,
                          path=f"{path}.{i}", issues=issues)
        return
    if not is_binding:
        issues.append(Issue(path, "binding"))
        return
    allowed = {"source", "value", "name", "path", "step", "transform", "args", "aspect"}
    if set(value) - allowed:
        issues.append(Issue(path, "unknown"))
    if value["source"] == "constant":
        if "value" not in value:
            issues.append(Issue(path, "required"))
        elif "transform" not in value:
            _constant(value["value"], target, context, path, issues)
        else:
            _transformed_constant(value, target, registry, context, path, issues)
        return
    source = binding_type(value, scope, context)
    if source is None:
        issues.append(Issue(path, "reference"))
        return
    source = transformed_type(value, source, registry)
    if source is None or not compatible(source, target):
        issues.append(Issue(path, "type"))


def binding_type(value: dict, scope: BindingScope, context: DefinitionContext) -> TypeSpec | None:
    source = value.get("source")
    if "aspect" in value:
        return STEP_STATE_TYPE if source == "step" and value["aspect"] == "state" and value.get("step") in scope.states and not value.get("path") else None
    root = {
        "parameter": scope.parameters.field(value.get("name", "")),
        "input": scope.parameters.field(value.get("name", "")),
        "context": context.context,
        "event": scope.event,
        "step": scope.steps.get(value.get("step", "")),
        "item": scope.items.get(value.get("step", "")),
        "error": ERROR_TYPE if value.get("step") in scope.errors else None,
    }.get(source)
    return at_path(root, value.get("path", ""))


def transformed_type(value: dict, source: TypeSpec, registry: AdapterRegistry) -> TypeSpec | None:
    ref = value.get("transform")
    if ref is None:
        return source
    extension = registry.extension("transform", str(ref))
    if extension is None or not isinstance(value.get("args", {}), dict):
        return None
    transform = extension.implementation
    if validate_value(transform.arguments, value.get("args", {})):
        return None
    if source.type not in transform.input_types:
        return None
    if ref == "list.first@1":
        return source.items
    if ref == "object.get@1":
        return at_path(source, value.get("args", {}).get("path", ""))
    if ref == "list.of_object@1":
        args = value.get("args", {})
        extra = args.get("extra", {})
        if not isinstance(extra, dict) or not isinstance(args.get("key", "value"), str):
            return None
        name = args.get("key", "value")
        fields = {name: replace(source, required=True, nullable=False)}
        fields.update({key: replace(infer_type(child), required=True) for key, child in extra.items()})
        return TypeSpec("array", items=TypeSpec("object", properties=tuple(fields.items())))
    return TypeSpec(transform.output_type) if transform.output_type != "any" else None


def infer_type(value: Any) -> TypeSpec:
    if isinstance(value, dict):
        return TypeSpec("object", properties=tuple((k, infer_type(v)) for k, v in value.items()))
    if isinstance(value, list):
        return TypeSpec("array", items=infer_type(value[0]) if value else TypeSpec("string"))
    return TypeSpec({str: "string", int: "integer", float: "number", bool: "boolean"}.get(type(value), "string"),
                    nullable=value is None)


def check_untyped(value: Any, **kwargs) -> None:
    """An adapter's open object still cannot smuggle an unchecked reference."""
    if isinstance(value, dict) and isinstance(value.get("source"), str):
        if value["source"] == "constant":
            target = TypeSpec("json", nullable=True)
        else:
            target = binding_type(value, kwargs["scope"], kwargs["context"])
            if target:
                target = transformed_type(value, target, kwargs["registry"])
        if target is None:
            kwargs["issues"].append(Issue(kwargs["path"], "reference"))
        else:
            check_binding(value, target, **kwargs)
    elif isinstance(value, dict | list):
        items = value.items() if isinstance(value, dict) else enumerate(value)
        for key, child in items:
            check_untyped(child, **{**kwargs, "path": f"{kwargs['path']}.{key}"})
    else:
        kwargs["issues"].append(Issue(kwargs["path"], "binding"))


def _constant(value, target, context, path, issues):
    if target.required and (value is None and not target.nullable or isinstance(value, str) and not value.strip()):
        issues.append(Issue(path, "required"))
    issues.extend(Issue(f"{path}.{issue.path}", issue.code) for issue in validate_value(target, value))
    if target.type == "file" and isinstance(value, dict) and value.get("fileId") not in context.files:
        issues.append(Issue(path, "reference"))
    if target.type == "object" and isinstance(value, dict):
        for name, child in target.properties:
            if name in value:
                _check_files(value[name], child, context, f"{path}.{name}", issues)
    if target.type == "array" and isinstance(value, list) and target.items:
        for i, child in enumerate(value):
            _check_files(child, target.items, context, f"{path}.{i}", issues)


def _check_files(value, target, context, path, issues):
    if target.type in {"file", "object", "array"}:
        _constant(value, target, context, path, issues)


def _transformed_constant(binding, target, registry, context, path, issues):
    source = infer_type(binding.get("value"))
    if transformed_type(binding, source, registry) is None:
        issues.append(Issue(path, "type"))
        return
    try:
        transform = registry.extension("transform", binding["transform"]).implementation
        result = transform.apply(binding["value"], **binding.get("args", {}))
        _constant(result, target, context, path, issues)
    except (ValueError, TypeError, ArithmeticError, KeyError):
        issues.append(Issue(path, "type"))
