"""Private multipart and streaming endpoints; no URL/base64 import path exists."""

from uuid import UUID

from django.core.files.uploadhandler import TemporaryFileUploadHandler
from django.http import FileResponse
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from chatballs.ai.external_agents.auth import authenticated, authorize_session
from chatballs.ai.external_agents.contracts import validate
from chatballs.ai.external_agents.file_access import load
from chatballs.ai.external_agents.file_models import ExternalAgentFile
from chatballs.ai.external_agents.file_streaming import scoped_stream
from chatballs.ai.external_agents.file_uploads import (
    FileConflict,
    abandon,
    complete,
    receipt,
    reserve,
    write,
)
from chatballs.ai.external_agents.file_validation import metadata
from chatballs.ai.external_agents.views import ProtocolView
from chatballs.conversations.attachment_policy import MAX_FILE_BYTES
from chatballs.tenancy.database import tenant_atomic


class BoundedUpload(TemporaryFileUploadHandler):
    def receive_data_chunk(self, raw_data, start):
        if start + len(raw_data) > MAX_FILE_BYTES:
            self.file.close()
            raise ValueError("payload_too_large")
        return super().receive_data_chunk(raw_data, start)


class UploadView(ProtocolView):
    parser_classes = [MultiPartParser]

    def post(self, request, connection_id, conversation_id):
        header = request.headers.get("Authorization")
        # Authenticate before parsing, then release all control locks during the upload.
        with authenticated(header) as (_, connection):
            self.check_connection(connection, connection_id)
        request._request.upload_handlers = [BoundedUpload(request._request)]
        if set(request.data) != {"uploadId", "authorizationId", "file", "sha256"}:
            raise ValueError("invalid_request")
        if any(len(request.data.getlist(key)) != 1 for key in request.data):
            raise ValueError("invalid_request")
        upload = request.FILES.get("file")
        if upload is None:
            raise ValueError("invalid_request")
        try:
            upload_id = UUID(request.data["uploadId"])
        except (TypeError, ValueError, AttributeError) as error:
            raise ValueError("invalid_request") from error
        if request.headers.get("Idempotency-Key") != str(upload_id):
            raise ValueError("invalid_request")
        values = metadata(upload, filename=upload.name, mime_type=upload.content_type)
        if values["sha256"] != request.data["sha256"]:
            raise ValueError("invalid_request")
        with authenticated(header) as (context, connection):
            session = authorize_session(context, connection, conversation_id=conversation_id,
                authorization_id=request.data["authorizationId"], operation="files.write")
            record, created = reserve(context, session, upload_id, values)
        if created:
            try:
                with tenant_atomic(context):
                    write(record, upload)
                with authenticated(header) as (context, connection):
                    authorize_session(context, connection, conversation_id=conversation_id,
                        authorization_id=request.data["authorizationId"], operation="files.write")
                    current = ExternalAgentFile.objects.select_for_update().get(pk=record.pk)
                    if current.file.name != record.file.name or current.released or current.complete:
                        raise FileConflict()
                    complete(context, record)
            except Exception:
                with tenant_atomic(context):
                    abandon(context, record)
                raise
        result = receipt(record)
        validate("catalogs.yaml", "UploadReceipt", result)
        return Response(result, status=201 if created else 200)


class FileView(ProtocolView):
    def get(self, request, connection_id, conversation_id, file_id):
        with authenticated(request.headers.get("Authorization")) as (context, connection):
            self.check_connection(connection, connection_id)
            session = authorize_session(context, connection, conversation_id=conversation_id,
                authorization_id=request.query_params.get("authorizationId"), operation="files.read")
            record = load(session, file_id)
            stream = record.file.open("rb")
            response = FileResponse(stream, content_type=record.mime_type,
                                    as_attachment=True, filename=record.filename)
            response.streaming_content = scoped_stream(request, stream, connection_id, conversation_id, file_id)
        response["X-Content-Type-Options"] = "nosniff"
        return response
