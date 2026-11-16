"""Bounded WSGI/ASGI streams stop when the current file grant is revoked."""

from asgiref.sync import sync_to_async
from django.core.handlers.asgi import ASGIRequest
from django.http import Http404
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from chatballs.ai.external_agents.auth import authenticated, authorize_session
from chatballs.ai.external_agents.file_access import load
from chatballs.ai.external_agents.file_validation import CHUNK


def scoped_stream(request, stream, connection_id, conversation_id, file_id):
    header = request.headers.get("Authorization")
    authorization_id = request.query_params.get("authorizationId")

    def read():
        try:
            with authenticated(header) as (context, connection):
                if connection.pk != connection_id:
                    return b""
                session = authorize_session(context, connection, conversation_id=conversation_id,
                    authorization_id=authorization_id, operation="files.read")
                load(session, file_id)
                return stream.read(CHUNK)
        except (AuthenticationFailed, PermissionDenied, Http404):
            return b""

    def synchronous():
        try:
            while data := read():
                yield data
        finally:
            stream.close()

    async def asynchronous():
        try:
            while data := await sync_to_async(read, thread_sensitive=True)():
                yield data
        finally:
            await sync_to_async(stream.close, thread_sensitive=True)()

    return asynchronous() if isinstance(request._request, ASGIRequest) else synchronous()
