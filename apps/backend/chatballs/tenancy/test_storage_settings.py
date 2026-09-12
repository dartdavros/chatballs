"""Хранилище файлов: локально по умолчанию, S3 из настроек админа, чтение из обоих мест."""

from __future__ import annotations

from tempfile import TemporaryDirectory
from unittest import mock

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, storages
from django.test import TestCase, override_settings

from chatballs.identity.models import EmployeeRole, HumanUser, Organization, OrganizationMembership
from chatballs.tenancy import storage_settings as ss
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.storage_backends import DynamicTenantStorage
from chatballs.tenancy.storage_migration import migrate_local_to_s3
from chatballs.testing import TenantAPIClient


class _FakeS3Factory:
    """Подменяет build_s3_storage: «бакет» — отдельный локальный каталог."""

    def __init__(self, root: str) -> None:
        self.root = root
        self.calls = 0

    def __call__(self, config, **kwargs):
        self.calls += 1
        return FileSystemStorage(location=self.root)


class StorageSettingsTests(TestCase):
    def setUp(self) -> None:
        self.media = TemporaryDirectory()
        self.bucket = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.addCleanup(self.bucket.cleanup)
        override = override_settings(MEDIA_ROOT=self.media.name)
        override.enable()
        self.addCleanup(override.disable)
        ss.invalidate_cache()
        self.addCleanup(ss.invalidate_cache)
        DynamicTenantStorage._s3_cache = None

        self.organization = Organization.objects.create(name="Acme", slug="acme")
        self.owner = HumanUser.objects.create_user(
            email="owner@example.com", password="Password-123", full_name="Owner", is_instance_admin=True
        )
        OrganizationMembership.objects.create(organization=self.organization, user=self.owner, role=EmployeeRole.OWNER, position_title="Owner")
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.owner)
        self.key = f"organizations/{self.organization.public_id}/probe/a.txt"

    def _enable_s3(self) -> _FakeS3Factory:
        factory = _FakeS3Factory(self.bucket.name)
        patcher = mock.patch.object(ss, "build_s3_storage", factory)
        patcher.start()
        self.addCleanup(patcher.stop)
        row = ss.StorageSettings.load()
        row.backend = ss.StorageBackend.S3
        row.s3_bucket = "demo"
        row.s3_access_key = "AKIA-demo-access"
        row.s3_secret_key = "very-secret"
        row.save()
        DynamicTenantStorage._s3_cache = None
        return factory

    def test_default_is_local_disk(self) -> None:
        self.assertEqual(ss.current_config().backend, ss.StorageBackend.LOCAL)
        with tenant_atomic(self.organization.id):
            storages["default"].save(self.key, ContentFile(b"local"))
        self.assertTrue((__import__("pathlib").Path(self.media.name) / self.key).exists())

    def test_s3_from_settings_and_reads_legacy_local_files(self) -> None:
        with tenant_atomic(self.organization.id):
            storages["default"].save(self.key, ContentFile(b"before switch"))
        self._enable_s3()
        new_key = f"organizations/{self.organization.public_id}/probe/b.txt"
        with tenant_atomic(self.organization.id):
            storage = storages["default"]
            storage.save(new_key, ContentFile(b"after switch"))
            # Новый файл — в «бакете», старый читается с локального диска.
            self.assertTrue((__import__("pathlib").Path(self.bucket.name) / new_key).exists())
            self.assertFalse((__import__("pathlib").Path(self.media.name) / new_key).exists())
            with storage.open(self.key) as handle:
                self.assertEqual(handle.read(), b"before switch")
            self.assertTrue(storage.exists(self.key))
            storage.delete(self.key)
            self.assertFalse(storage.exists(self.key))

    def test_unreachable_secondary_storage_does_not_break_local_writes(self) -> None:
        """Недоступное второе хранилище не должно ронять работу с активным.

        Реквизиты S3 остаются в строке настроек и после возврата на локальный
        диск (чтобы дочитать файлы из бакета). Если бакет недоступен —
        выключенный MinIO, устаревшие ключи, — перезапись и удаление файла на
        локальном диске обязаны продолжать работать.
        """
        row = ss.StorageSettings.load()
        row.backend = ss.StorageBackend.LOCAL
        row.s3_bucket = "demo"
        row.s3_access_key = "AKIA-demo-access"
        row.s3_secret_key = "very-secret"
        row.save()
        DynamicTenantStorage._s3_cache = None

        class _DeadS3:
            def exists(self, name):
                raise OSError("Could not connect to the endpoint URL")

            def delete(self, name):
                raise OSError("Could not connect to the endpoint URL")

        patcher = mock.patch.object(ss, "build_s3_storage", lambda *args, **kwargs: _DeadS3())
        patcher.start()
        self.addCleanup(patcher.stop)

        with tenant_atomic(self.organization.id):
            storage = storages["default"]
            storage.save(self.key, ContentFile(b"local"))
            self.assertTrue(storage.exists(self.key))
            # Перезапись одноимённого файла: сначала удаление, потом запись.
            storage.delete(self.key)
            self.assertFalse(storage.exists(self.key))
            storage.save(self.key, ContentFile(b"replaced"))
            with storage.open(self.key) as handle:
                self.assertEqual(handle.read(), b"replaced")

    def test_secrets_are_encrypted_at_rest_and_masked_in_api(self) -> None:
        self._enable_s3()
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT s3_secret_key FROM tenancy_storagesettings WHERE id = 1")
            stored = cursor.fetchone()[0]
        self.assertNotEqual(stored, "very-secret")
        self.assertEqual(ss.StorageSettings.load().s3_secret_key, "very-secret")
        payload = self.client.get("/api/v1/instance/storage/").json()["storage"]
        self.assertEqual(payload["backend"], "S3")
        self.assertNotIn("s3SecretKey", payload)
        self.assertTrue(payload["s3HasSecretKey"])
        self.assertNotIn("demo-access", payload["s3AccessKeyMasked"].replace("…", ""))

    def test_patch_to_s3_probes_before_switching(self) -> None:
        with mock.patch.object(ss, "build_s3_storage", side_effect=RuntimeError("connection refused")):
            response = self.client.patch(
                "/api/v1/instance/storage/",
                {"backend": "S3", "s3Bucket": "demo", "s3AccessKey": "a", "s3SecretKey": "b"},
                format="json",
            )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("недоступно", response.json()["errors"]["s3Bucket"])
        self.assertEqual(ss.StorageSettings.load().backend, ss.StorageBackend.LOCAL)

        factory = _FakeS3Factory(self.bucket.name)
        with mock.patch.object(ss, "build_s3_storage", factory):
            response = self.client.patch(
                "/api/v1/instance/storage/",
                {"backend": "S3", "s3Bucket": "demo", "s3EndpointUrl": "https://s3.example.com/", "s3AccessKey": "a", "s3SecretKey": "b"},
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.content)
        row = ss.StorageSettings.load()
        self.assertEqual(row.backend, ss.StorageBackend.S3)
        self.assertEqual(row.s3_endpoint_url, "https://s3.example.com")
        self.assertIsNotNone(row.s3_verified_at)
        # Пустые секреты в повторном PATCH оставляют прежние.
        with mock.patch.object(ss, "build_s3_storage", factory):
            self.client.patch("/api/v1/instance/storage/", {"backend": "S3", "s3AccessKey": "", "s3SecretKey": ""}, format="json")
        self.assertEqual(ss.StorageSettings.load().s3_secret_key, "b")

    def test_check_endpoint_reports_errors_without_saving(self) -> None:
        response = self.client.post("/api/v1/instance/storage/check/", {"s3Bucket": ""}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("s3Bucket", response.json()["errors"])
        self.assertEqual(ss.StorageSettings.load().s3_bucket, "")

    def test_employee_cannot_change_storage(self) -> None:
        employee = HumanUser.objects.create_user(email="staff@example.com", password="Password-123")
        OrganizationMembership.objects.create(organization=self.organization, user=employee, role=EmployeeRole.EMPLOYEE, position_title="Op")
        client = TenantAPIClient()
        client.force_authenticate(employee)
        self.assertEqual(client.get("/api/v1/instance/storage/").status_code, 403)
        self.assertEqual(client.patch("/api/v1/instance/storage/", {"backend": "LOCAL"}, format="json").status_code, 403)

    def test_migration_copies_local_files_to_s3(self) -> None:
        with tenant_atomic(self.organization.id):
            storages["default"].save(self.key, ContentFile(b"legacy"))
        self._enable_s3()
        response = self.client.post("/api/v1/instance/storage/migrate/")
        self.assertEqual(response.status_code, 202, response.content)
        row = ss.StorageSettings.load()
        self.assertEqual(row.migration_status, ss.StorageMigrationStatus.RUNNING)
        copied = migrate_local_to_s3(row)
        self.assertEqual(copied, 1)
        self.assertTrue((__import__("pathlib").Path(self.bucket.name) / self.key).exists())
        self.assertEqual(self.client.post("/api/v1/instance/storage/migrate/").status_code, 409)
