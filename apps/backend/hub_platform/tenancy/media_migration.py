from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.db import transaction

from hub_platform.ai.models import KnowledgeAttachment, attachment_upload_path
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.models import OrganizationStorageUsage


@dataclass(frozen=True, slots=True)
class MediaCopyEntry:
    attachment_id: int
    source_key: str
    target_key: str
    size: int
    sha256: str
    status: str

    def payload(self) -> dict[str, int | str]:
        return asdict(self)


def _sha256_path(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _sha256_storage(key: str) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with default_storage.open(key, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _source_path(source_root: Path, source_key: str) -> Path:
    root = source_root.resolve()
    candidate = (root / source_key).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError(f"Source key escapes source root: {source_key}")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def _target_key(attachment: KnowledgeAttachment) -> str:
    filename = Path(attachment.original_name).name
    return attachment_upload_path(attachment, filename)


def copy_attachment(
    *,
    attachment: KnowledgeAttachment,
    source_root: Path,
    apply: bool,
) -> MediaCopyEntry:
    source_key = attachment.file.name
    target_key = _target_key(attachment)
    source_path = _source_path(source_root, source_key)
    source_hash, source_size = _sha256_path(source_path)
    status = "verified"

    if apply:
        if default_storage.exists(target_key):
            target_hash, target_size = _sha256_storage(target_key)
            if (target_hash, target_size) != (source_hash, source_size):
                raise ValueError(f"Destination hash mismatch: {target_key}")
            status = "already-copied"
        else:
            with source_path.open("rb") as source:
                stored_key = default_storage.save(target_key, File(source))
            if stored_key != target_key:
                raise ValueError(f"Storage changed target key to {stored_key}")
            target_hash, target_size = _sha256_storage(target_key)
            if (target_hash, target_size) != (source_hash, source_size):
                raise ValueError(f"Copied object hash mismatch: {target_key}")
            status = "copied"
        attachment.file.name = target_key
        attachment.size = source_size
        attachment.save(update_fields=["file", "size"])

    return MediaCopyEntry(
        attachment_id=attachment.id,
        source_key=source_key,
        target_key=target_key,
        size=source_size,
        sha256=source_hash,
        status=status,
    )


@transaction.atomic
def reconcile_attachment_storage_usage(*, context: TenantContext) -> int:
    total = sum(
        KnowledgeAttachment.objects.filter(organization=context.organization).values_list(
            "size", flat=True
        )
    )
    OrganizationStorageUsage.objects.update_or_create(
        organization=context.organization,
        defaults={"bytes_used": total},
    )
    return total
