"""Validate complete definitions without invoking action handlers or granting access."""

from __future__ import annotations

import json

from chatballs.integrations.adapters.registry import AdapterRegistry, default_registry
from chatballs.integrations.adapters.schema import SchemaDefinitionError
from chatballs.integrations.scenarios.bindings import BindingScope
from chatballs.integrations.scenarios.blocks import BlockValidator
from chatballs.integrations.scenarios.definition import (
    FORMAT_VERSION,
    DefinitionContext,
    Issue,
    empty_definition,
)
from chatballs.integrations.scenarios.synchronization import check_synchronization
from chatballs.integrations.scenarios.triggers import check_access, check_triggers
from chatballs.integrations.scenarios.types import read_type


def validate_definition(document, *, context: DefinitionContext, registry: AdapterRegistry | None = None) -> list[Issue]:
    try:
        return _validate_definition(document, context=context, registry=registry)
    except (TypeError, KeyError, AttributeError, RecursionError):
        # Malformed untrusted JSON is an invalid document, never a server error.
        return [Issue("$", "structure")]


def _validate_definition(document, *, context: DefinitionContext, registry: AdapterRegistry | None = None) -> list[Issue]:
    issues = []
    if not isinstance(document, dict) or set(document) != set(empty_definition()):
        return [Issue("$", "structure")]
    if type(document["version"]) is not int or document["version"] != FORMAT_VERSION:
        return [Issue("version", "version")]
    try:
        if len(json.dumps(document, allow_nan=False)) > 1024 * 1024:
            return [Issue("$", "size")]
        parameters = read_type(document["parameters"])
        results = read_type(document["results"])
        if parameters.type != "object" or results.type != "object":
            raise ValueError("schema")
    except (TypeError, ValueError, RecursionError, SchemaDefinitionError):
        return [Issue("parameters", "schema")]
    registry = registry or default_registry()
    check_triggers(document["triggers"], context=context, path="triggers", issues=issues)
    check_access(document["access"], document["triggers"], issues, context)
    check_synchronization(document["synchronization"], context=context, issues=issues, registry=registry)
    scope = BindingScope(parameters)
    event_schemas = [context.events.get((str(t.get("connection", "")), t.get("event", "")))
                     for t in document["triggers"] if isinstance(t, dict)] if isinstance(document["triggers"], list) else []
    event_schemas = [spec for spec in event_schemas if spec]
    # A reference must be valid for every trigger that can launch this document.
    if event_schemas and len(event_schemas) == len(document["triggers"]) and all(spec == event_schemas[0] for spec in event_schemas):
        scope.event = event_schemas[0]
    validator = BlockValidator(context=context, registry=registry, issues=issues)
    validator.conditions(document["conditions"], scope, "conditions")
    validator.steps(document["steps"], scope)
    validator.binding(document["outputs"], results, scope, "outputs")
    if not document["steps"]:
        issues.append(Issue("steps", "required"))
    if not document["triggers"]:
        issues.append(Issue("triggers", "required"))
    return issues
