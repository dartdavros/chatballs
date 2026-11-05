"""Native transport and AI connection operations call product services."""

from functools import partial

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from rest_framework.exceptions import PermissionDenied

from chatballs.integrations import management
from chatballs.integrations.action_catalog import connection_schemas as schema
from chatballs.integrations.action_catalog.connection_results import safe_output
from chatballs.integrations.action_catalog.contracts import (
    NativeAccessDenied,
    NativeOperationRejected,
)
from chatballs.integrations.action_catalog.file_reads import FILE_RESULT, stream_result
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.action_catalog.serialization import json_data
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.deletion import IntegrationInUse
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat import asset_services


def invoke(context, values, *, service, by_id=False, body=False, file=False):
    args = [context.tenant]
    if by_id:
        args.append(values["integration_id"])
    if body:
        args.append(values)
    if file:
        name, content_type, content = context.open_file(values["file"]["fileId"])
        args.append(SimpleUploadedFile(name, content, content_type))
    try:
        result = service(*args)
        with tenant_atomic(context.tenant):
            result = safe_output(context.tenant, json_data(result))
    except (ObjectDoesNotExist, PermissionDenied):
        raise NativeAccessDenied("context") from None
    except (ValidationError, IntegrityError):
        raise NativeOperationRejected("arguments") from None
    except IntegrationInUse:
        raise NativeOperationRejected("conditions_unavailable") from None
    return OperationResult(ResultState.COMPLETED, result)


TARGET = obj(integration_id=schema.ID)
CHECK = obj(integration_id=schema.ID, capability=schema.named("capability",
    schema.enum(("stt", "tts"), "native.connection_capability")))
for key, method, route, view, inputs, outputs, service, by_id, body, effect, execution in (
    ("connections.get", "GET", "", "IntegrationListView", obj(), schema.LIST, management.listing, False, False, Effect.READ, "local"),
    ("connections.post", "POST", "", "IntegrationListView", schema.CREATE, schema.OUTPUT, management.create, False, True, Effect.CREATE, "io"),
    ("connections.detail.patch", "PATCH", "<int:integration_id>/", "IntegrationDetailView", schema.UPDATE, schema.OUTPUT, management.update, True, True, Effect.UPDATE, "io"),
    ("connections.detail.delete", "DELETE", "<int:integration_id>/", "IntegrationDetailView", TARGET, obj(), management.delete, True, False, Effect.DELETE, "io"),
    ("connections.test.post", "POST", "<int:integration_id>/test/", "IntegrationTestView", CHECK, schema.OUTPUT, management.checked, True, True, Effect.UPDATE, "io"),
    ("connections.tools.refresh.post", "POST", "<int:integration_id>/tools/refresh/", "IntegrationToolsRefreshView", TARGET, schema.OUTPUT,
        partial(management.checked, refresh=True), True, False, Effect.UPDATE, "io"),
    ("connections.tools.confirm.post", "POST", "<int:integration_id>/tools/read-only/confirm/", "IntegrationToolConfirmView",
        obj(integration_id=schema.ID, name=schema.field("toolName", required=True), confirmed=schema.field("confirmed", "boolean", required=True)),
        schema.OUTPUT, management.read_only, True, True, Effect.UPDATE, "local"),
    ("connections.tools.revoke.post", "POST", "<int:integration_id>/tools/read-only/revoke/", "IntegrationToolRevokeView",
        obj(integration_id=schema.ID, name=schema.field("toolName", required=True)), schema.OUTPUT,
        partial(management.read_only, revoke=True), True, True, Effect.UPDATE, "local"),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(invoke, service=service, by_id=by_id, body=body),
        capability="integrations.view" if method == "GET" else "integrations.manage", scope="organization",
        route=f"integrations/{route}", view=f"chatballs.integrations.views.{view}", method=method, effect=effect, execution=execution)

action(key="connections.address.post", title="native.connections.address.post", input=obj(url=schema.field("url", required=True)),
    output=obj(errors=schema.field("errors", "object", open=True)),
    handler=partial(invoke, service=management.address, body=True), capability="integrations.manage", scope="organization",
    route="integrations/http/validate-address/", view="chatballs.integrations.address_validation.HttpAddressValidationView",
    method="POST", effect=Effect.READ, execution="io")
action(key="connections.assets.post", title="native.connections.assets.post",
    input=obj(integration_id=schema.ID, file=schema.field("file", "file", required=True)), output=obj(url=schema.field("url")),
    handler=partial(invoke, service=asset_services.upload, by_id=True, file=True), capability="integrations.manage", scope="organization",
    route="integrations/<int:integration_id>/assets/", view="chatballs.webchat.asset_views.WidgetAssetUploadView",
    method="POST", effect=Effect.CREATE, execution="io")


def download(context, values):
    try:
        stream, name, content_type = asset_services.open_asset(values["public_id"], organization_id=context.tenant.organization_id)
    except ObjectDoesNotExist:
        raise NativeAccessDenied("context") from None
    return stream_result(context, stream, name, content_type)


action(key="connections.asset.get", title="native.connections.asset.get", input=obj(public_id=schema.field("publicId", required=True)),
    output=FILE_RESULT, handler=download, capability="", scope="organization",
    route="api/v1/webchat/assets/<uuid:public_id>/", view="chatballs.webchat.asset_views.WidgetAssetView", method="GET", effect=Effect.READ, execution="io")
