import hashlib
import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

from chatballs.ai.knowledge_categories import ensure_uncategorized_category
from chatballs.ai.models import Knowledge, KnowledgeAttachment
from chatballs.identity.models import Organization
from chatballs.tenancy.models import OrganizationStorageUsage

_DESTINATION_ROOT = Path(tempfile.mkdtemp(prefix="c04-destination-media-"))


@override_settings(MEDIA_ROOT=_DESTINATION_ROOT)
class TenantMediaMigrationTests(TestCase):
    def setUp(self) -> None:
        self.source_root = Path(tempfile.mkdtemp(prefix="c04-source-media-"))
        self.organization = Organization.objects.create(name="Media", slug="media")
        knowledge = Knowledge.objects.create(
            organization=self.organization,
            category=ensure_uncategorized_category(self.organization),
            title="Legacy",
        )
        self.attachment = KnowledgeAttachment.objects.create(
            organization=self.organization,
            knowledge=knowledge,
            file="legacy/price.txt",
            original_name="price.txt",
            size=0,
        )
        source = self.source_root / self.attachment.file.name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"legacy media")

    def test_dry_run_hashes_without_mutating_database_or_source(self) -> None:
        manifest = self.source_root / "dry-run.json"
        call_command(
            "migrate_tenant_media",
            "--organization-public-id",
            str(self.organization.public_id),
            "--source-root",
            str(self.source_root),
            "--manifest",
            str(manifest),
        )

        self.attachment.refresh_from_db()
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(self.attachment.file.name, "legacy/price.txt")
        self.assertEqual(
            payload["entries"][0]["sha256"],
            hashlib.sha256(b"legacy media").hexdigest(),
        )
        self.assertFalse(payload["apply"])
        self.assertTrue((self.source_root / "legacy/price.txt").exists())

    def test_apply_copies_verifies_updates_usage_and_keeps_source(self) -> None:
        manifest = self.source_root / "apply.json"
        call_command(
            "migrate_tenant_media",
            "--organization-public-id",
            str(self.organization.public_id),
            "--source-root",
            str(self.source_root),
            "--manifest",
            str(manifest),
            "--apply",
        )

        self.attachment.refresh_from_db()
        expected_prefix = f"organizations/{self.organization.public_id}/"
        destination = _DESTINATION_ROOT / self.attachment.file.name
        self.assertTrue(self.attachment.file.name.startswith(expected_prefix))
        self.assertEqual(destination.read_bytes(), b"legacy media")
        self.assertTrue((self.source_root / "legacy/price.txt").exists())
        self.assertEqual(
            OrganizationStorageUsage.objects.get(
                organization=self.organization
            ).bytes_used,
            len(b"legacy media"),
        )
        self.assertFalse(json.loads(manifest.read_text(encoding="utf-8"))["sourceDeleted"])
