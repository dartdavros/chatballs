"""Small shared schema constructors; product parameters remain explicit."""

from dataclasses import replace

from chatballs.integrations.action_catalog.contracts import APIEntry, NativeAction
from chatballs.integrations.action_catalog.registry import register_action
from chatballs.integrations.adapters.contracts import (
    DEFAULT_LIMITS,
    Effect,
    OperationDescriptor,
    OperationHandlers,
)
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec


def obj(**fields):
    return TypeSpec("object", properties=tuple((name, spec if spec.title_key else
        replace(spec, title_key=f"native.fields.{name}")) for name, spec in fields.items()))


def required(spec):
    return replace(spec, required=True)


def enum(values, prefix):
    return TypeSpec("enum", options=tuple(EnumOption(value, f"{prefix}.{value}") for value in values))


def labelled_codes(values, prefix, fallback, *, nullable=False):
    """Open diagnostic vocabulary: retain codes, present known/fallback labels."""
    return TypeSpec("string", options=tuple(EnumOption(value, f"{prefix}.{value}") for value in values),
        placeholder_key=fallback, nullable=nullable)


IDENTIFIER = TypeSpec("integer", required=True)
CONVERSATION_ID = TypeSpec("string", required=True, pattern=r"[1-9]\d{0,17}",
    title_key="scenarios.conversation_number")
TEXT = TypeSpec("string")
BOOLEAN = TypeSpec("boolean")


def action(*, key, title, input, output, handler, capability, scope,
           route, view, method, execution="local", effect=None, extra_entries=(), limits=DEFAULT_LIMITS,
           authority="tenant", surface="app"):
    operation = OperationDescriptor(key=key, title_key=title,
        input=input, output=output, handlers=OperationHandlers(),
        effect=effect or (Effect.READ if method == "GET" else Effect.UPDATE),
        permission_scope=scope, limits=limits)
    return register_action(NativeAction(operation, handler, capability, scope,
        (APIEntry(route, method, view, surface),) + tuple(extra_entries), execution, authority=authority))
