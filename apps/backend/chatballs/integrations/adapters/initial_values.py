"""Explicit, typed context bindings for opening a manual create form."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InitialValue:
    target: str
    source: str
    transform: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)


def validate_initial_values(operation, registry):
    from chatballs.integrations.adapters.contracts import Effect
    from chatballs.integrations.scenarios.bindings import transformed_type
    from chatballs.integrations.scenarios.catalog import CONTEXT
    from chatballs.integrations.scenarios.types import at_path, compatible

    problems = []
    targets = []
    for binding in operation.initial_values:
        if operation.effect != Effect.CREATE:
            problems.append("manual initial values require a create operation")
        parts = binding.target.split(".")
        target = at_path(operation.input, binding.target)
        source = at_path(CONTEXT, binding.source)
        if not all(parts) or target is None or target.secret:
            problems.append(f"initial value {binding.target}: unknown or secret target")
            continue
        if any(binding.target == path or binding.target.startswith(path + ".")
               or path.startswith(binding.target + ".") for path in targets):
            problems.append(f"initial value {binding.target}: overlapping target")
        targets.append(binding.target)
        transform = {"transform": binding.transform, "args": binding.arguments} if binding.transform else {}
        resolved = transformed_type(transform, source, registry) if source else None
        if resolved is None or not compatible(resolved, target):
            problems.append(f"initial value {binding.target}: incompatible context binding")
    return problems
