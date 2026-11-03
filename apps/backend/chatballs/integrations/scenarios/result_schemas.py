"""Typed aggregate results use the same shapes in validation and execution."""

from dataclasses import replace

from chatballs.integrations.adapters.schema import EnumOption, TypeSpec
from chatballs.integrations.scenarios.bindings import ERROR_TYPE


def entry_schema(steps, context, depth=0):
    fields = []
    if depth > 16:
        return TypeSpec("object")
    for block in steps:
        output = block_output(block, context, depth + 1)
        if output:
            fields.append((block["id"], replace(output, required=False)))
    return TypeSpec("object", properties=(
        ("index", TypeSpec("integer", required=True, title_key="runs.item_index")),
        ("state", TypeSpec("enum", required=True, title_key="runs.item_state", options=tuple(
            EnumOption(state, f"runs.state_{state}") for state in ("completed", "failed", "cancelled")))),
        ("steps", TypeSpec("object", title_key="runs.block_results", properties=tuple(fields))),
        ("error", replace(ERROR_TYPE, nullable=True, title_key="runs.block_errors")),
    ))


def block_output(block, context, depth=0):
    kind = block.get("kind")
    if kind == "action":
        pair = context.operations.get((str(block.get("connection", "")), block.get("target", "")))
        return pair[1] if pair else None
    if kind == "call":
        pair = context.scenarios.get(str(block.get("scenario", "")))
        return pair[1] if pair else None
    if kind == "foreach":
        entry = entry_schema(block.get("body", []), context, depth)
        return TypeSpec("object", properties=(
            ("items", TypeSpec("array", title_key="runs.iteration_results", items=entry)),
            ("errors", TypeSpec("array", title_key="runs.iteration_errors", items=entry)),
        ))
    if kind == "parallel":
        return TypeSpec("object", properties=(("branches", TypeSpec("object", title_key="runs.parallel_results",
            properties=tuple((str(i), entry_schema(steps, context, depth)) for i, steps in enumerate(block.get("branches", []))))),))
    if kind == "wait" and block.get("mode") == "event":
        payload = context.events.get((str(block.get("connection", "")), block.get("event", "")))
        return TypeSpec("object", properties=(("event", replace(payload, required=False)),)) if payload else None
    return None
