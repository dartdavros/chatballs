"""Evaluate only guards whose inputs are known before a manual form is filled."""

from chatballs.integrations.execution.conditions import evaluate_conditions
from chatballs.integrations.execution.permissions import ExecutionDenied, context_values
from chatballs.integrations.execution.source_support import require_supported_sources
from chatballs.integrations.scenarios.values import RunValues, resolve_value


def known_binding(binding, parameters):
    if isinstance(binding, list):
        return all(known_binding(child, parameters) for child in binding)
    if not isinstance(binding, dict):
        return True  # The normal resolver will reject a malformed known binding.
    source = binding.get("source")
    if source is None:
        return all(known_binding(child, parameters) for child in binding.values())
    if source in {"parameter", "input"}:
        return binding.get("name") in parameters
    return source in {"constant", "context"}


def known_inputs(bindings, conversation, parameters, *, registry=None):
    values = RunValues(parameters=parameters, context=context_values(conversation))
    result = {}
    for name, binding in bindings.items():
        if not known_binding(binding, parameters):
            continue
        try:
            result[name] = resolve_value(binding, values, registry)
        except (KeyError, IndexError, TypeError, ValueError, ArithmeticError):
            raise ExecutionDenied("arguments") from None
    return result


def require_known_conditions(document, conversation, *, parameters=None, registry=None):
    require_supported_sources(document)
    parameters = parameters or {}
    results = []
    for condition in document["conditions"]["items"]:
        bindings = [condition.get("left", {})]
        if condition.get("op") not in {"empty", "filled"}:
            bindings.append(condition.get("right", {}))
        if condition.get("kind") is None and not all(known_binding(value, parameters) for value in bindings):
            results.append(None)
            continue
        single = {"conditions": {"mode": "all", "items": [condition]}, "steps": []}
        results.append(evaluate_conditions(single, conversation, parameters, registry=registry))
    # Unknown form inputs are not evidence that a guard is false. An all-group
    # needs every known predicate; an any-group is impossible only if all fail.
    impossible = (False in results if document["conditions"]["mode"] == "all"
                  else bool(results) and all(value is False for value in results))
    if impossible:
        raise ExecutionDenied("conditions_not_met")
