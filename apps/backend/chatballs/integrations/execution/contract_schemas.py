"""Serialize trusted TypeSpec contracts, retaining secret and validation flags."""

from dataclasses import asdict

from chatballs.integrations.adapters.schema import EnumOption, TypeSpec


def write_spec(spec):
    return asdict(spec)


def read_spec(value):
    data = dict(value)
    data["properties"] = tuple((name, read_spec(child)) for name, child in data.get("properties", []))
    data["options"] = tuple(EnumOption(**option) for option in data.get("options", []))
    if data.get("items") is not None:
        data["items"] = read_spec(data["items"])
    return TypeSpec(**data)


def frozen_schemas(run, step, operation):
    from chatballs.integrations.execution.actions import step_target
    target = step_target(step)
    saved = run.definition.get("contracts", {}).get(f"{target['connection']}:{target['target']}")
    if saved and "input" in saved:
        return read_spec(saved["input"]), read_spec(saved["output"])
    # Old snapshots have no schema copy: withhold values if their original
    # version is unavailable rather than applying a different redaction schema.
    return (operation.input, operation.output) if operation else (None, None)
