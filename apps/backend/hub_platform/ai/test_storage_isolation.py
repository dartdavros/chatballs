import tempfile

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from hub_platform.ai.knowledge_categories import ensure_uncategorized_category
from hub_platform.ai.models import Knowledge
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import Organization
from hub_platform.tenancy.database import tenant_atomic
from hub_platform.tenancy.models import OrganizationStorageUsage
from hub_platform.testing import TenantAPIClient, system_tenant_context

_MEDIA_ROOT = tempfile.mkdtemp(prefix="c04-storage-isolation-")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class TenantStorageIsolationTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(
            email="owner@edevs.tech",
            password="temporary-password",
        )
        self.organization = Organization.objects.get(slug="edevs")
        self.knowledge = Knowledge.objects.create(
            organization=self.organization,
            category=ensure_uncategorized_category(self.organization),
            title="Storage isolation",
        )
        self.client = TenantAPIClient()
        self.client.login(
            username="owner@edevs.tech",
            password="temporary-password",
        )

    def _upload(self):
        return self.client.post(
            f"/api/v1/ai/knowledge/{self.knowledge.id}/attachments/",
            data={"file": SimpleUploadedFile("price.txt", b"tenant bytes")},
            format="multipart",
        )

    def test_upload_uses_prefix_quota_and_matching_context(self) -> None:
        self.assertEqual(self._upload().status_code, 201)
        attachment = self.knowledge.attachments.get()
        self.assertTrue(
            attachment.file.name.startswith(
                f"organizations/{self.organization.public_id}/"
            )
        )
        self.assertEqual(
            OrganizationStorageUsage.objects.get(
                organization=self.organization
            ).bytes_used,
            len(b"tenant bytes"),
        )

        other = Organization.objects.create(name="Other", slug="storage-other")
        with self.assertRaises(SuspiciousFileOperation):
            default_storage.exists(attachment.file.name)
        with tenant_atomic(system_tenant_context(other)):
            with self.assertRaises(SuspiciousFileOperation):
                default_storage.exists(attachment.file.name)
        with tenant_atomic(system_tenant_context(self.organization)):
            self.assertTrue(default_storage.exists(attachment.file.name))

    def test_delete_releases_storage_usage(self) -> None:
        attachment_id = self._upload().json()["attachment"]["id"]
        response = self.client.delete(
            f"/api/v1/ai/knowledge/{self.knowledge.id}/attachments/{attachment_id}/"
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            OrganizationStorageUsage.objects.get(
                organization=self.organization
            ).bytes_used,
            0,
        )
