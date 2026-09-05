from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from chatballs.ai.models import KnowledgeAttachment
from chatballs.identity.models import Organization
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.media_migration import (
    copy_attachment,
    reconcile_attachment_storage_usage,
)


class Command(BaseCommand):
    help = (
        "Copy one organization's legacy media to tenant-prefixed storage, verify "
        "SHA-256 and write an immutable manifest. Source files are never deleted."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization-public-id", required=True)
        parser.add_argument("--source-root", required=True)
        parser.add_argument("--manifest", required=True)
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Copy and update DB keys. Without this flag only verification runs.",
        )

    def handle(self, *args, **options) -> None:
        try:
            organization = Organization.objects.get(
                public_id=options["organization_public_id"]
            )
        except (Organization.DoesNotExist, ValueError) as error:
            raise CommandError("Organization not found") from error

        source_root = Path(options["source_root"])
        manifest_path = Path(options["manifest"])
        if not source_root.is_dir():
            raise CommandError(f"Source root does not exist: {source_root}")
        if manifest_path.exists():
            raise CommandError("Manifest already exists; refusing to overwrite it")

        context = TenantContext.for_resource(organization)
        entries = []
        try:
            with tenant_atomic(context):
                attachments = list(
                    KnowledgeAttachment.objects.filter(organization=organization)
                    .select_related("knowledge", "organization")
                    .order_by("id")
                )
                for attachment in attachments:
                    entries.append(
                        copy_attachment(
                            attachment=attachment,
                            source_root=source_root,
                            apply=options["apply"],
                        )
                    )
                usage = (
                    reconcile_attachment_storage_usage(context=context)
                    if options["apply"]
                    else sum(entry.size for entry in entries)
                )
                manifest_path.parent.mkdir(parents=True, exist_ok=True)
                manifest_path.write_text(
                    json.dumps(
                        {
                            "version": 1,
                            "createdAt": datetime.now(UTC).isoformat(),
                            "organizationPublicId": str(organization.public_id),
                            "apply": bool(options["apply"]),
                            "sourceRoot": str(source_root.resolve()),
                            "storageBytes": usage,
                            "entries": [entry.payload() for entry in entries],
                            "sourceDeleted": False,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
        except (FileNotFoundError, OSError, ValueError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            self.style.SUCCESS(
                f"Verified {len(entries)} objects, {usage} bytes; manifest={manifest_path}"
            )
        )
