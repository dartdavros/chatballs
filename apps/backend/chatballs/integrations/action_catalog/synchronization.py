"""Typed exchange settings use the existing synchronization validator."""

from dataclasses import replace
from functools import partial

from chatballs.integrations.action_catalog.scenarios import invoke
from chatballs.integrations.action_catalog.schema import action, enum, obj
from chatballs.integrations.adapters.contracts import Effect
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.scenarios import synchronization_management


def field(name, kind="string", **kwargs):
    return TypeSpec(kind, title_key=f"native.sync_fields.{name}", **kwargs)


def choices(name, values):
    return replace(enum(values, "native.sync_values"), title_key=f"native.sync_fields.{name}", required=True)


SIDE = obj(connection=field("connection", required=True), entity=field("entity", required=True))
VALUE = obj(**{"from": field("from", "json", nullable=True, required=True), "to": field("to", "json", nullable=True, required=True)})
MAPPING = obj(left=field("left", required=True), right=field("right", required=True),
    direction=choices("direction", ("forward", "reverse")), values=field("values", "array", items=VALUE),
    transform=field("transform"), args=field("args", "json"))
PAIR = obj(id=field("pair", required=True), enabled=field("enabled", "boolean", required=True),
    left=replace(SIDE, title_key="native.sync_fields.left", required=True),
    right=replace(SIDE, title_key="native.sync_fields.right", required=True),
    direction=choices("direction", ("forward", "reverse", "both")), fields=field("fields", "array", items=MAPPING, required=True),
    sourceOfTruth=choices("sourceOfTruth", ("left", "right", "latest")),
    conflict=choices("conflict", ("source", "latest", "manual")), deletion=choices("deletion", ("unlink", "keep", "propagate")),
    causality=replace(obj(suppressEcho=field("suppressEcho", "boolean", required=True),
        requireExplicitLink=field("requireExplicitLink", "boolean", required=True)), title_key="native.sync_fields.causality", required=True))
DOCUMENT = obj(version=field("version", "integer", required=True),
    synchronization=field("pairs", "array", items=PAIR, required=True))
OUTPUT = obj(revision=field("revision", "integer"), definition=replace(DOCUMENT, title_key="native.sync_fields.definition"),
    result=field("result", "json", nullable=True), error=field("error"))


def save(tenant, data):
    return synchronization_management.save(tenant, data["connection_id"],
        {"revision": data["revision"], "definition": data["definition"]})


for method, inputs, service, arguments, body in (
    ("GET", obj(connection_id=field("connection", "integer", required=True)), synchronization_management.detail, ("connection_id",), False),
    ("PUT", obj(connection_id=field("connection", "integer", required=True), revision=field("revision", "integer", required=True),
        definition=replace(DOCUMENT, title_key="native.sync_fields.definition", required=True)), save, (), True),
):
    key = f"synchronization.{method.lower()}"
    action(key=key, title=f"native.{key}", input=inputs, output=OUTPUT,
        handler=partial(invoke, service=service, arguments=arguments, body=body),
        capability="integrations.manage", scope="organization", route="integrations/services/<int:connection_id>/synchronization/",
        view="chatballs.integrations.scenarios.synchronization_views.ServiceSynchronizationView", method=method,
        effect=Effect.READ if method == "GET" else Effect.UPDATE)
