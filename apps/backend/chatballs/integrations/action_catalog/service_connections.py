"""Service actions use the ordinary application service and its network boundary."""

from functools import partial

from django.core.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied

from chatballs.integrations.action_catalog import service_schemas as schema
from chatballs.integrations.action_catalog.contracts import (
    NativeAccessDenied,
    NativeOperationRejected,
)
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.action_catalog.serialization import json_data
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.deletion import IntegrationInUse
from chatballs.integrations.models import Integration
from chatballs.integrations.service_connections import management as commands
from chatballs.integrations.service_connections import management_reads as reads


def invoke(context, values, *, service, arguments=(), body=False):
    args = [context.tenant, *(values[key] for key in arguments)]
    if body:
        args.append(values)
    try:
        result = service(*args)
    except (Integration.DoesNotExist, PermissionDenied):
        raise NativeAccessDenied("context") from None
    except ValidationError:
        raise NativeOperationRejected("arguments") from None
    except IntegrationInUse:
        raise NativeOperationRejected("conditions_unavailable") from None
    except commands.ManagementCheckFailed:
        # The service has already persisted status and its audit. No provider
        # diagnostics or credential values become a normal action output.
        return OperationResult(ResultState.FAILED, error_code="conditions_unavailable")
    return OperationResult(ResultState.COMPLETED, json_data(result))


for key, method, route, view, inputs, outputs, service, arguments, body, effect, execution, capability in (
    ("services.adapters.get", "GET", "service-adapters/", "ServiceAdapterListView",
        obj(), schema.CATALOG, reads.adapters, (), False, Effect.READ, "local", "integrations.view"),
    ("services.get", "GET", "services/", "ServiceConnectionListView",
        obj(), schema.LIST, reads.listing, (), False, Effect.READ, "local", "integrations.view"),
    ("services.post", "POST", "services/", "ServiceConnectionListView",
        schema.CREATE, schema.OUTPUT, commands.create, (), True, Effect.CREATE, "io", "integrations.manage"),
    ("services.detail.get", "GET", "services/<int:connection_id>/", "ServiceConnectionDetailView",
        obj(connection_id=schema.ID), schema.OUTPUT, reads.detail, ("connection_id",), False, Effect.READ, "local", "integrations.view"),
    ("services.detail.patch", "PATCH", "services/<int:connection_id>/", "ServiceConnectionDetailView",
        schema.UPDATE, schema.OUTPUT, commands.update, ("connection_id",), True, Effect.UPDATE, "local", "integrations.manage"),
    ("services.detail.delete", "DELETE", "services/<int:connection_id>/", "ServiceConnectionDetailView",
        obj(connection_id=schema.ID), obj(), commands.delete, ("connection_id",), False, Effect.DELETE, "io", "integrations.manage"),
    ("services.check.post", "POST", "services/<int:connection_id>/check/", "ServiceConnectionCheckView",
        schema.CHECK, schema.OUTPUT, commands.check, ("connection_id",), True, Effect.UPDATE, "io", "integrations.manage"),
    ("services.access.post", "POST", "services/<int:connection_id>/access/", "ServiceConnectionAccessView",
        schema.REPLACE, schema.OUTPUT, commands.replace_access, ("connection_id",), True, Effect.UPDATE, "io", "integrations.manage"),
    ("services.lookup.get", "GET", "services/<int:connection_id>/lookups/<slug:key>/", "ServiceLookupView",
        schema.LOOKUP, schema.LOOKUP_RESULT, commands.lookup, ("connection_id", "key"), False, Effect.READ, "io", "integrations.manage"),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(invoke, service=service, arguments=arguments, body=body), capability=capability,
        scope="organization", route=f"integrations/{route}",
        view=f"chatballs.integrations.service_connections.views.{view}", method=method, effect=effect, execution=execution)

