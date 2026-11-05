"""Tenant file access, optionally restricted to an invocation's input references."""

from chatballs.integrations.models import ServiceFile
from chatballs.tenancy.database import tenant_atomic


def file_opener(organization_id, *, allowed=None, max_bytes=None):
    def open_file(file_id):
        if allowed is not None and str(file_id) not in allowed:
            raise ServiceFile.DoesNotExist
        with tenant_atomic(organization_id):
            record = ServiceFile.objects.get(public_id=file_id, organization_id=organization_id)
            if max_bytes is not None and record.size > max_bytes:
                raise ValueError("file_too_large")
            with record.file.open("rb") as stream:
                data = stream.read() if max_bytes is None else stream.read(max_bytes + 1)
            if len(data) != record.size or max_bytes is not None and len(data) > max_bytes:
                raise ValueError("file_size_mismatch")
            return record.name, record.content_type, data

    return open_file
