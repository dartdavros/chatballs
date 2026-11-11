"""Проверка описания адаптера до регистрации (SPEC-0037 R-3).

Объявленная возможность обязана иметь обработчик: долгая операция —
продолжение, стратегия сверки — reconcile, отменяемая — cancel, событие
webhook/callback — приём, событие опроса — poll. Проверка доступа ссылается
только на операцию чтения, поэтому скрытых бизнес-изменений не делает.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from chatballs.integrations.adapters.contracts import (
    READ_EFFECTS,
    AdapterDescriptor,
    Delivery,
    Mode,
    OperationDescriptor,
    RetryStrategy,
    ScenarioTemplate,
)
from chatballs.integrations.adapters.schema import SchemaDefinitionError, TypeSpec, validate_spec

if TYPE_CHECKING:
    from chatballs.integrations.adapters.registry import AdapterRegistry

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")


def validate_adapter(adapter: AdapterDescriptor, registry: AdapterRegistry) -> list[str]:
    problems: list[str] = []
    if not KEY_PATTERN.match(adapter.key):
        problems.append("bad adapter key")
    if adapter.contract_version < 1:
        problems.append("contract_version must be positive")
    if not registry.has_extension("transport", adapter.transport):
        problems.append(f"unknown transport extension {adapter.transport}")
    if adapter.listed and not adapter.auth_methods:
        problems.append("listed adapter needs an auth method")
    _schema(problems, "settings", adapter.settings)
    problems.extend(_controls(adapter.settings, registry))
    _unique(problems, "operation", [item.key for item in adapter.operations])
    _unique(problems, "auth method", [item.key for item in adapter.auth_methods])
    _unique(problems, "event", [item.key for item in adapter.events])
    _unique(problems, "lookup", [item.key for item in adapter.lookups])
    _unique(problems, "entity", [item.key for item in adapter.entities])
    for entity in adapter.entities:
        from chatballs.integrations.adapters.entity_contracts import validate_entity
        problems.extend(validate_entity(adapter, entity))
        _schema(problems, f"entity {entity.key}", entity.fields)
        problems.extend(_controls(entity.fields, registry))
    for operation in adapter.operations:
        problems.extend(f"operation {operation.key}: {item}" for item in _operation(operation, registry))
    for method in adapter.auth_methods:
        problems.extend(f"auth {method.key}: {item}" for item in _auth(adapter, method, registry))
    for event in adapter.events:
        _schema(problems, f"event {event.key}", event.payload)
        if event.delivery in (Delivery.WEBHOOK, Delivery.CALLBACK) and not callable(event.ingress):
            problems.append(f"event {event.key}: ingress handler is missing")
        if event.delivery == Delivery.POLL and not callable(event.poll):
            problems.append(f"event {event.key}: poll handler is missing")
    for lookup in adapter.lookups:
        source = adapter.operation(lookup.operation)
        if source is None or source.effect not in READ_EFFECTS:
            problems.append(f"lookup {lookup.key}: needs a read operation")
    for template in adapter.templates:
        problems.extend(f"template {template.key}: {item}" for item in _template(adapter, template, registry))
    return problems


def _operation(operation: OperationDescriptor, registry: AdapterRegistry) -> list[str]:
    from chatballs.integrations.adapters.initial_values import validate_initial_values

    problems: list[str] = []
    problems.extend(validate_initial_values(operation, registry))
    if not KEY_PATTERN.match(operation.key):
        problems.append("bad key")
    for category in operation.category_path:
        if not KEY_PATTERN.fullmatch(category.key) or not category.title_key:
            problems.append("bad category")
    _schema(problems, "input", operation.input)
    _schema(problems, "output", operation.output)
    for spec in (operation.input, operation.output):
        problems.extend(_controls(spec, registry))
    handlers = operation.handlers
    if not callable(handlers.execute):
        problems.append("execute handler is missing")
    if operation.mode == Mode.LONG and not callable(handlers.resume):
        problems.append("long operation needs resume handler")
    if operation.retry == RetryStrategy.RECONCILE and not callable(handlers.reconcile):
        problems.append("reconcile strategy needs reconcile handler")
    if operation.retry == RetryStrategy.SAFE_READ and operation.effect not in READ_EFFECTS:
        problems.append("safe_read strategy is only for read operations")
    if operation.cancellable and not callable(handlers.cancel):
        problems.append("cancellable operation needs cancel handler")
    return problems


def _auth(adapter: AdapterDescriptor, method, registry: AdapterRegistry) -> list[str]:
    problems: list[str] = []
    if not registry.has_extension("auth", method.extension):
        problems.append(f"unknown auth extension {method.extension}")
    _schema(problems, "fields", method.fields)
    _unique(problems, "settings/auth field", [name for name, _ in adapter.settings.properties + method.fields.properties])
    problems.extend(_controls(method.fields, registry))
    if method.check is not None:
        operation = adapter.operation(method.check.operation)
        if operation is None or operation.effect not in READ_EFFECTS:
            problems.append("check must use a read operation")
        if method.check.inputs is not None:
            _schema(problems, "check inputs", method.check.inputs)
            problems.extend(_controls(method.check.inputs, registry))
    return problems


def _template(adapter: AdapterDescriptor, template: ScenarioTemplate, registry: AdapterRegistry) -> list[str]:
    problems: list[str] = []
    if template.version < 1:
        problems.append("version must be positive")
    if not template.steps and template.definition is None:
        problems.append("template needs steps")
    if template.definition is not None:
        from chatballs.integrations.adapters.template_labels import label_target
        from chatballs.integrations.scenarios.definition import DefinitionContext
        from chatballs.integrations.scenarios.validation import validate_definition
        context = DefinitionContext(connections={"self"}, operations={
            ("self", f"service:{operation.key}"): (operation.input, operation.output) for operation in adapter.operations
        })
        issues = validate_definition(template.definition, context=context, registry=registry)
        structural = {"structure", "unknown", "version", "schema", "block", "trigger", "identifier", "size", "binding"}
        problems += [f"{issue.path}: {issue.code}" for issue in issues if issue.code in structural]
        for path, title_key in template.labels:
            try:
                label_target(template.definition, path)
                if not isinstance(title_key, str) or not title_key:
                    raise ValueError("label translation key must be text")
            except ValueError as error:
                problems.append(str(error))
    elif template.labels:
        problems.append("labels require a complete definition")
    _schema(problems, "parameters", template.parameters)
    problems.extend(_controls(template.parameters, registry))
    _unique(problems, "step", [step.id for step in template.steps])
    for step in template.steps:
        scope, _, name = step.target.partition(":")
        if scope == "service":
            if adapter.operation(name) is None:
                problems.append(f"step {step.id}: unknown operation {name}")
        elif scope != "chatballs" or not name:
            problems.append(f"step {step.id}: bad target {step.target}")
        for ref in _transforms(step.inputs):
            if not registry.has_extension("transform", ref):
                problems.append(f"step {step.id}: unknown transform {ref}")
    return problems


def _transforms(value: object) -> list[str]:
    if isinstance(value, dict):
        found = [str(value["transform"])] if "transform" in value else []
        return found + [ref for child in value.values() for ref in _transforms(child)]
    if isinstance(value, list):
        return [ref for child in value for ref in _transforms(child)]
    return []


def _controls(spec: TypeSpec, registry: AdapterRegistry) -> list[str]:
    problems = []
    if spec.control:
        extension = registry.extension("control", spec.control)
        if extension is None:
            problems.append(f"unknown control {spec.control}")
        elif spec.type not in extension.implementation.types:
            problems.append(f"control {spec.control} does not support {spec.type}")
    for _name, child in spec.properties:
        problems.extend(_controls(child, registry))
    if spec.items is not None:
        problems.extend(_controls(spec.items, registry))
    return problems


def _schema(problems: list[str], where: str, spec: TypeSpec) -> None:
    try:
        validate_spec(spec)
    except SchemaDefinitionError as error:
        problems.append(f"{where}: {error}")


def _unique(problems: list[str], what: str, keys: list[str]) -> None:
    if len(keys) != len(set(keys)):
        problems.append(f"duplicate {what} key")
