"""Durable reservation before storage IO; only complete files receive receipts."""

import hashlib
from datetime import timedelta
from uuid import uuid4

from django.core.files import File
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework.exceptions import APIException

from chatballs.ai.external_agents.file_models import ExternalAgentFile
from chatballs.ai.external_agents.payloads import utc
from chatballs.tenancy.storage_quota import finalize_storage, release_storage, reserve_storage


class FileConflict(APIException):
    status_code = 409
    default_code = "idempotency_conflict"


def receipt(record):
    return {"version": "1", "fileId": str(record.public_id), "mimeType": record.mime_type,
            "filename": record.filename, "size": record.size, "sha256": record.sha256,
            "expiresAt": utc(record.expires_at)}


def reservation_key(record):
    return f"external-file:{record.public_id}:{record.file.name.rsplit('/', 1)[-1]}"


def reserve(context, session, upload_id, values):
    scope = hashlib.sha256(f"{session.connection_id}:{session.conversation_id}:{upload_id}".encode()).hexdigest()
    record = ExternalAgentFile.objects.select_for_update().filter(upload_scope=scope).first()
    if record:
        if (record.authorization_id != session.authorization_id
                or any(getattr(record, key) != value for key, value in values.items())):
            raise FileConflict()
        if record.expires_at <= timezone.now():
            raise FileConflict(code="snapshot_expired")
        if record.complete and not record.released:
            return record, False
        if not record.released:
            if record.attempted_at > timezone.now() - timedelta(minutes=15):
                raise FileConflict(code="conversation_busy")
            abandon(context, record)
    else:
        record = ExternalAgentFile(session=session, authorization_id=session.authorization_id,
            upload_id=upload_id, upload_scope=scope, expires_at=timezone.now() + timedelta(hours=24), **values)
    # Persist the exact attempted object key before storage sees a byte. A process
    # crash leaves a discoverable orphan, not an untracked public file.
    record.file.name = f"organizations/{context.organization.public_id}/external-files/{uuid4().hex}"
    record.released = False
    record.attempted_at = timezone.now()
    record.save()
    reserve_storage(context=context, expected_bytes=record.size, idempotency_key=reservation_key(record))
    return record, True


def write(record, upload):
    key = default_storage.save(record.file.name, File(upload))
    if key != record.file.name:
        default_storage.delete(key)
        raise FileConflict()
    if default_storage.size(key) != record.size:
        raise ValueError("invalid_request")


def complete(context, record):
    record.complete = True
    record.save(update_fields=["complete"])
    finalize_storage(context=context, idempotency_key=reservation_key(record), actual_bytes=record.size)


def abandon(context, record):
    persisted = ExternalAgentFile.objects.select_for_update().filter(pk=record.pk).first()
    # A lost commit acknowledgement is retried by uploadId. Never remove bytes
    # if the completion actually committed, even when the caller observed failure.
    if persisted and persisted.complete and persisted.file.name == record.file.name:
        return
    if record.file.name:
        default_storage.delete(record.file.name)
    release_storage(context=context, idempotency_key=reservation_key(record))
    ExternalAgentFile.objects.filter(pk=record.pk, file=record.file.name, complete=False).update(released=True)
