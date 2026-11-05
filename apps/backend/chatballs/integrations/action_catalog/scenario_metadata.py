"""Executable metadata reads without turning launch protocols into actions."""

from functools import partial

from chatballs.integrations.action_catalog.run_management import field
from chatballs.integrations.action_catalog.scenarios import METADATA_LIMITS, invoke
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.adapters.contracts import Effect
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.execution import lookup_queries, manual_catalog_queries


def catalog(tenant, data):
    return manual_catalog_queries.catalog(tenant, {key: str(value) for key, value in data.items()})


def approval(tenant, data):
    return lookup_queries.approval(tenant, data["public_id"], data)


LOOKUP = obj(items=field("items", "array", items=obj(value=field("value", "json", nullable=True), label=field("label"))))
CATALOG = obj(items=field("items", "array", items=TypeSpec("json")), files=field("files", "array", items=TypeSpec("json")))

for key, route, view, inputs, outputs, service, execution in (
    ("runs.actions.get", "run-actions/", "launch_views.ManualActionsView", obj(conversation=field("conversation", "integer")),
        CATALOG, catalog, "local"),
    ("runs.lookup.get", "run-actions/lookup/", "metadata_views.ManualLookupView",
        obj(connection=field("connection", "integer", required=True), conversation=field("conversation", "integer", required=True),
            operation=field("operation", required=True), scenario=field("scenario"), lookup=field("lookup", required=True)),
        LOOKUP, lookup_queries.manual, "io"),
    ("runs.approval_lookup.get", "runs/<uuid:public_id>/approval-lookup/", "ai_metadata.ApprovalLookupView",
        obj(public_id=field("run", required=True), path=field("path", required=True), lookup=field("lookup", required=True)),
        LOOKUP, approval, "io"),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(invoke, service=service, body=True), capability="", scope="organization",
        route=f"integrations/{route}", view=f"chatballs.integrations.execution.{view}", method="GET",
        effect=Effect.READ, execution=execution, limits=METADATA_LIMITS)
