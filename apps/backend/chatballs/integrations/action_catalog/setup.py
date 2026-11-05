"""Bootstrap has its own one-time guard; a tenant grant cannot enter it."""

from django.core.exceptions import ValidationError
from django.http import Http404

from chatballs.identity import demo_media, setup_commands
from chatballs.identity.setup import SetupAlreadyCompleted, instance_needs_setup
from chatballs.integrations.action_catalog.authority import require_context
from chatballs.integrations.action_catalog.contracts import (
    NativeAccessDenied,
    NativeOperationRejected,
)
from chatballs.integrations.action_catalog.file_reads import FILE_RESULT, stream_result
from chatballs.integrations.action_catalog.profile_schemas import field
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.adapters.schema import validate_value

INPUT = obj(organizationName=field("organizationName", required=True), fullName=field("fullName", required=True),
    email=field("email", required=True), password=field("password", required=True, secret=True),
    installDemo=field("installDemo", "boolean"), language=field("language"))
MEDIA_INPUT = obj(name=field("name", required=True))


def status(context, values):
    require_context(context, "bootstrap")
    if validate_value(obj(), values):
        raise NativeOperationRejected("arguments")
    return OperationResult(ResultState.COMPLETED, {"needsSetup": instance_needs_setup()})


def finish(context, values):
    require_context(context, "bootstrap")
    if validate_value(INPUT, values) or not context.public_host or context.public_scheme not in {"http", "https"}:
        raise NativeOperationRejected("arguments")
    try:
        result = setup_commands.finish(values, public_host=context.public_host, public_scheme=context.public_scheme)
    except SetupAlreadyCompleted:
        raise NativeAccessDenied("permission") from None
    except ValidationError:
        raise NativeOperationRejected("arguments") from None
    # The original HTTP ceremony logs in the owner. A catalog result must not
    # mint a session or return the submitted password or a session credential.
    return OperationResult(ResultState.COMPLETED, {"organizationPublicId": str(result.organization.public_id), "ownerId": result.owner.pk})


def media(context, values):
    require_context(context, "bootstrap")
    if validate_value(MEDIA_INPUT, values) or not callable(context.store_file):
        raise NativeOperationRejected("arguments")
    try:
        stream, content_type = demo_media.open_avatar(values["name"])
    except Http404:
        raise NativeAccessDenied("context") from None
    return stream_result(context, stream, values["name"], content_type)


for key, route, view, method, inputs, outputs, handler, effect, execution in (
    ("setup.get", "api/v1/setup/", "setup_views.SetupStatusView", "GET", obj(), obj(needsSetup=field("needsSetup", "boolean")), status, Effect.READ, "local"),
    ("setup.complete", "api/v1/setup/complete/", "setup_views.SetupView", "POST", INPUT, obj(organizationPublicId=field("organizationPublicId"), ownerId=field("ownerId", "integer")), finish, Effect.CREATE, "io"),
    ("setup.demo_media.get", "api/v1/demo-media/avatars/<str:name>", "demo_views.DemoMediaView", "GET", MEDIA_INPUT, FILE_RESULT, media, Effect.READ, "io"),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs, handler=handler, capability="", scope="bootstrap",
        authority="bootstrap", route=route, view=f"chatballs.identity.{view}", method=method, effect=effect, execution=execution)
