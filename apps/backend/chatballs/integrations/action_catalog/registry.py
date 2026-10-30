"""Trusted product metadata for the common editor, without a fake executor.

Domain modules register their schemas here. Execution is deliberately absent
from this module: T-170/T-174–176 attach domain services and permission checks.
"""

from dataclasses import dataclass

from chatballs.integrations.adapters.schema import TypeSpec, validate_spec


@dataclass(frozen=True)
class ActionSchema:
    key: str
    title_key: str
    input: TypeSpec
    output: TypeSpec
    permission_scope: str


_ACTIONS: dict[str, ActionSchema] = {}


def register_action_schema(schema: ActionSchema):
    if schema.key in _ACTIONS:
        raise ValueError(f"Duplicate action: {schema.key}")
    validate_spec(schema.input)
    validate_spec(schema.output)
    _ACTIONS[schema.key] = schema


def action_schemas():
    return tuple(_ACTIONS.values())


# Metadata needed by installed presets; no link is created when editing.
register_action_schema(ActionSchema(
    key="entity_link.create", title_key="scenarios.link_action", permission_scope="conversation",
    input=TypeSpec("object", properties=(
        ("connection", TypeSpec("integer", required=True, title_key="scenarios.connection")),
        ("entity", TypeSpec("string", required=True, title_key="scenarios.entity")),
        ("external_id", TypeSpec("string", required=True, title_key="scenarios.external_id")),
    )),
    output=TypeSpec("object", properties=(("id", TypeSpec("string")),)),
))
