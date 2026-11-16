"""A file ID is useful only with a current grant from this exact authorization."""

from django.core.files.storage import default_storage
from django.http import Http404
from django.utils import timezone

from chatballs.ai.external_agents.file_models import ExternalAgentFile, ExternalAgentFileGrant
from chatballs.ai.external_agents.file_validation import metadata
from chatballs.conversations.models import Message, MessageKind


def content(record, caption=""):
    return {"type": "image" if record.mime_type.startswith("image/") else "file",
            "fileId": str(record.public_id), "filename": record.filename,
            "mimeType": record.mime_type, "size": record.size, "sha256": record.sha256, "caption": caption}


def grant_message(row, message):
    if (message.kind != MessageKind.FILE or not message.attachment or message.audio
            or "/voice/" in message.attachment.name):
        raise ValueError("unsupported_content")
    record = ExternalAgentFile.objects.filter(source_message=message).first()
    if record is None:
        with message.attachment.open("rb") as stream:
            values = metadata(stream, filename=message.attachment_name, mime_type=message.attachment_content_type)
        record = ExternalAgentFile.objects.create(organization_id=row.organization_id,
            authorization_id=row.authorization_id, source_message=message,
            file=message.attachment.name, owned=False, complete=True, **values)
    return content(record, message.text)


def issue(row, contents):
    for value in contents:
        if value.get("type") in ("file", "image"):
            record = ExternalAgentFile.objects.get(public_id=value["fileId"])
            ExternalAgentFileGrant.objects.get_or_create(file=record, request=row,
                defaults={"authorization_id": row.authorization_id})


def load(session, file_id):
    # Do not let malformed opaque IDs reach PostgreSQL's UUID cast.
    from uuid import UUID

    try:
        file_id = UUID(str(file_id))
    except (ValueError, TypeError, AttributeError) as error:
        raise Http404 from error
    record = ExternalAgentFile.objects.filter(public_id=file_id, organization_id=session.organization_id,
                                               complete=True, released=False).first()
    if record is None:
        raise Http404
    own = (record.session_id == session.pk and record.authorization_id == session.authorization_id
           and record.expires_at and record.expires_at > timezone.now())
    issued = record.grants.filter(request__session=session, authorization_id=session.authorization_id,
                                  request__deadline_at__gt=timezone.now()).exists()
    if not own and not issued:
        raise Http404
    if not record.owned:
        message = Message.including_tests.filter(pk=record.source_message_id, conversation_id=session.conversation_id,
                                         kind=MessageKind.FILE, audio="", attachment=record.file.name).first()
        if message is None:
            raise Http404
    if not record.file or "/voice/" in record.file.name or not default_storage.exists(record.file.name):
        raise Http404
    return record


def verify(session, supplied):
    record = load(session, supplied["fileId"])
    expected = content(record, supplied["caption"])
    if supplied["type"] == "file":
        expected["type"] = "file"
    if expected != supplied:
        raise ValueError("invalid_request")
    with record.file.open("rb") as stream:
        values = metadata(stream, filename=record.filename, mime_type=record.mime_type)
    if any(getattr(record, key) != value for key, value in values.items()):
        raise ValueError("invalid_request")
    return record
