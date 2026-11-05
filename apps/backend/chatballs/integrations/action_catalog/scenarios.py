"""Definition actions preserve product revisions, permissions and secret output rules."""

from functools import partial

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from rest_framework.exceptions import PermissionDenied

from chatballs.integrations.action_catalog import scenario_schemas as schema
from chatballs.integrations.action_catalog.contracts import (
    NativeAccessDenied,
    NativeOperationRejected,
)
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.action_catalog.serialization import json_data
from chatballs.integrations.adapters.contracts import Effect, Limits, OperationResult, ResultState
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenarios import management
from chatballs.integrations.scenarios.catalog_queries import catalog
from chatballs.integrations.scenarios.definition_redaction import safe_definition
from chatballs.integrations.scenarios.services import RevisionConflict
from chatballs.tenancy.database import tenant_atomic


def invoke(context, values, *, service, arguments=(), body=False, updating=False):
    kwargs = {"public_id": values["public_id"]} if updating else {}
    args = [context.tenant, *(values.get(key) for key in arguments)]
    if body:
        args.append({key: value for key, value in values.items() if not updating or key != "public_id"})
    try:
        result = service(*args, **kwargs)
        with tenant_atomic(context.tenant):
            row = result.get("scenario", {})
            if "definition" in row:
                row["definition"] = safe_definition(context.tenant, row["definition"])
    except (ObjectDoesNotExist, PermissionDenied):
        raise NativeAccessDenied("context") from None
    except (ValidationError, management.InvalidDefinition):
        raise NativeOperationRejected("arguments") from None
    except (ExecutionDenied, RevisionConflict):
        raise NativeOperationRejected("state_changed") from None
    return OperationResult(ResultState.COMPLETED, json_data(result))


def listing(tenant, connection):
    return management.listing(tenant, connection=connection or "")


def save(tenant, values, **kwargs):
    settings = values.pop("settings", None)
    if not isinstance(settings, dict) or set(settings) - {"definition", "agentPolicies"}:
        raise ValidationError("settings")
    return management.save(tenant, {**values, **settings}, **kwargs)


def check(tenant, settings):
    if not isinstance(settings, dict):
        raise ValidationError("settings")
    return management.check(tenant, settings.get("definition"))


# Metadata includes the schemas of the whole installed catalog, bounded
# independently from ordinary business responses and the root's data budget.
METADATA_LIMITS = Limits(max_response_bytes=4 * 1024 * 1024)
for key, method, route, view, inputs, outputs, service, arguments, body, updating, effect in (
    ("scenarios.get", "GET", "scenarios/", "ScenarioListView", obj(connection=schema.field("connection", "integer")),
        schema.LIST, listing, ("connection",), False, False, Effect.READ),
    ("scenarios.post", "POST", "scenarios/", "ScenarioListView", schema.CREATE,
        schema.OUTPUT, save, (), True, False, Effect.CREATE),
    ("scenarios.detail.get", "GET", "scenarios/<uuid:public_id>/", "ScenarioDetailView", obj(public_id=schema.ID),
        schema.OUTPUT, management.detail, ("public_id",), False, False, Effect.READ),
    ("scenarios.detail.put", "PUT", "scenarios/<uuid:public_id>/", "ScenarioDetailView", schema.UPDATE,
        schema.OUTPUT, save, (), True, True, Effect.UPDATE),
    ("scenarios.detail.delete", "DELETE", "scenarios/<uuid:public_id>/", "ScenarioDetailView", obj(public_id=schema.ID, revision=schema.REVISION),
        obj(), management.delete, ("public_id", "revision"), False, False, Effect.DELETE),
    ("scenarios.check.post", "POST", "scenarios/check/", "ScenarioCheckView", obj(settings=schema.SETTINGS),
        obj(valid=schema.field("valid", "boolean"), issues=schema.ISSUES), check, ("settings",), False, False, Effect.READ),
    ("scenarios.copy.post", "POST", "scenarios/<uuid:public_id>/copy/", "ScenarioCopyView", obj(public_id=schema.ID, name=schema.field("name", required=True)),
        schema.OUTPUT, management.copy, ("public_id", "name"), False, False, Effect.CREATE),
    ("scenarios.preset.post", "POST", "services/<int:connection_id>/presets/<slug:key>/", "ScenarioPresetView",
        obj(connection_id=schema.field("connection", "integer", required=True), key=schema.field("preset", required=True)),
        schema.OUTPUT, management.preset, ("connection_id", "key"), False, False, Effect.CREATE),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(invoke, service=service, arguments=arguments, body=body, updating=updating),
        capability="integrations.manage", scope="organization", route=f"integrations/{route}",
        view=f"chatballs.integrations.scenarios.views.{view}", method=method, effect=effect, limits=METADATA_LIMITS)

action(key="scenarios.catalog.get", title="native.scenarios.catalog.get", input=obj(), output=schema.CATALOG,
    handler=partial(invoke, service=catalog), capability="integrations.manage", scope="organization",
    route="integrations/scenarios/catalog/", view="chatballs.integrations.scenarios.catalog_views.ScenarioCatalogView",
    method="GET", effect=Effect.READ, limits=METADATA_LIMITS)
