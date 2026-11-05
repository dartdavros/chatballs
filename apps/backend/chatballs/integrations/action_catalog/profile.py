"""Global personal actions cannot be granted to tenant scenarios or agents."""

from functools import partial

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from chatballs.identity import profile_commands, profile_files, profile_language, profile_sessions
from chatballs.integrations.action_catalog import profile_schemas as schema
from chatballs.integrations.action_catalog.administrative import register
from chatballs.integrations.action_catalog.authority import current_user, require_context
from chatballs.integrations.action_catalog.contracts import (
    NativeAccessDenied,
    NativeOperationRejected,
)
from chatballs.integrations.action_catalog.file_reads import FILE_RESULT, stream_result
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.action_catalog.serialization import json_data
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.adapters.schema import validate_value

for key, suffix, inputs, service in (
    ("profile.patch", "update/", obj(fullName=schema.field("fullName", required=True), email=schema.field("email", required=True)), profile_commands.update),
    ("profile.appearance.patch", "appearance/", obj(theme=schema.field("uiTheme"), accent=schema.field("uiAccent")), profile_commands.appearance),
    ("profile.language.patch", "language/", obj(language=schema.field("language")), profile_language.update),
):
    register(key=key, method="POST", route=f"api/v1/auth/profile/{suffix}",
        view="chatballs.identity.auth.profile." + {"update/": "ProfileUpdateView", "appearance/": "ProfileAppearanceView", "language/": "ProfileLanguageView"}[suffix],
        inputs=inputs, outputs=schema.OUTPUT, service=service, body=True, audit=True, effect=Effect.UPDATE, authority="personal")


def invoke(context, values, *, operation, inputs):
    require_context(context, "personal")
    if validate_value(inputs, values):
        raise NativeOperationRejected("arguments")
    try:
        current_user(context.user)
        if operation == "read_avatar":
            if not callable(context.store_file):
                raise NativeAccessDenied("context")
            stream, content_type = profile_files.read(context.user)
            return stream_result(context, stream, "avatar", content_type)
        if operation == "upload_avatar":
            if not callable(context.open_file):
                raise NativeAccessDenied("context")
            name, content_type, content = context.open_file(values["file"]["fileId"])
            result = profile_files.upload(context.user, SimpleUploadedFile(name, content, content_type), request=context.request)
        elif operation == "delete_avatar":
            result = profile_files.delete(context.user, request=context.request)
        elif operation == "sessions":
            result = profile_sessions.read(context.user, context.session_key)
        else:
            result = profile_sessions.revoke_others(context.user, context.session_key, request=context.request)
    except (PermissionDenied, NotFound):
        raise NativeAccessDenied("permission") from None
    except ValidationError:
        raise NativeOperationRejected("arguments") from None
    return OperationResult(ResultState.COMPLETED, json_data(result.data))


for key, operation, method, suffix, view, inputs, outputs, effect, execution in (
    ("profile.avatar.get", "read_avatar", "GET", "avatar/", "ProfileAvatarView", obj(), FILE_RESULT, Effect.READ, "io"),
    ("profile.avatar.post", "upload_avatar", "POST", "avatar/", "ProfileAvatarView", obj(file=schema.field("file", "file", required=True)), schema.OUTPUT, Effect.UPDATE, "io"),
    ("profile.avatar.delete", "delete_avatar", "DELETE", "avatar/", "ProfileAvatarView", obj(), schema.OUTPUT, Effect.DELETE, "io"),
    ("profile.sessions.get", "sessions", "GET", "sessions/", "ProfileSessionsView", obj(), schema.SESSIONS, Effect.READ, "local"),
    ("profile.sessions.revoke", "revoke_sessions", "POST", "sessions/revoke-other/", "ProfileRevokeOtherSessionsView", obj(), obj(revoked=schema.field("revoked", "integer")), Effect.DELETE, "local"),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(invoke, operation=operation, inputs=inputs), capability="", scope="personal", authority="personal",
        route=f"api/v1/auth/profile/{suffix}", view=f"chatballs.identity.auth.profile.{view}", method=method, effect=effect, execution=execution)
