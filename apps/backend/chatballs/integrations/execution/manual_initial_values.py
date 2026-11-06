"""Read-only projection of an already authorized conversation into form values."""

from chatballs.integrations.adapters.contracts import Effect
from chatballs.integrations.adapters.schema import validate_value
from chatballs.integrations.execution.permissions import context_values
from chatballs.integrations.scenarios.types import at_path
from chatballs.integrations.scenarios.values import RunValues, resolve_value


def initial_values(operation, conversation):
    if conversation is None or operation.effect != Effect.CREATE:
        return {}
    actual = RunValues(context=context_values(conversation))
    result = {}
    for binding in operation.initial_values:
        reference = {"source": "context", "path": binding.source}
        try:
            value = resolve_value(reference, actual)
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
            if binding.transform:
                value = resolve_value({**reference, "transform": binding.transform,
                                       "args": binding.arguments}, actual)
        except (KeyError, IndexError, TypeError, ValueError, ArithmeticError):
            continue
        target = at_path(operation.input, binding.target)
        if target is None or validate_value(target, value):
            continue
        parent = result
        *parents, name = binding.target.split(".")
        for part in parents:
            parent = parent.setdefault(part, {})
        parent[name] = value
    return result
