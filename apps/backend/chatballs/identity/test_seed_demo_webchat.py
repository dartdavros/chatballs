"""Новые модели веб-чата в демонаборе: реестр, повторный запуск и удаление."""

from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed import service
from chatballs.identity.demo_seed.registry import _delete_record, runtime_recording
from chatballs.identity.setup import SetupInput, complete_setup
from chatballs.identity.test_seed_demo import OWNER
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.models import OrganizationStorageUsage
from chatballs.webchat.appearance import DEFAULTS
from chatballs.webchat.assets import upload_widget_asset
from chatballs.webchat.models import WebChatWidget, WidgetAsset


class DemoWebChatTests(TestCase):
    def setUp(self) -> None:
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        override = override_settings(MEDIA_ROOT=media.name)
        override.enable()
        self.addCleanup(override.disable)
        result = complete_setup(SetupInput(**OWNER))
        self.context = TenantContext.for_resource(result.organization)
        with tenant_atomic(self.context):
            self.dataset = DemoDataset.objects.create(
                organization=result.organization, status=DemoDatasetStatus.INSTALLING,
            )
            self.dataset = service.install(context=self.context, dataset=self.dataset)
        self.assertEqual(self.dataset.status, DemoDatasetStatus.INSTALLED, self.dataset.error)

    def _add_demo_asset(self) -> WidgetAsset:
        upload = SimpleUploadedFile(
            "icon.svg", b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            b'<rect x="0" y="0" width="16" height="16"/></svg>',
        )
        with tenant_atomic(self.context), runtime_recording(self.dataset):
            widget = WebChatWidget.objects.order_by("id").first()
            return upload_widget_asset(context=self.context, integration=widget.integration, upload=upload)

    def test_widget_asset_is_registered_without_changing_widget_appearance(self) -> None:
        asset = self._add_demo_asset()
        with tenant_atomic(self.context):
            self.assertTrue(asset.file.storage.exists(asset.file.name))
        self.assertTrue(self.dataset.records.filter(
            content_type__model="widgetasset", object_id=str(asset.pk),
        ).exists())
        self.assertEqual(asset.integration.config["appearance"], DEFAULTS)

    def test_asset_removal_deletes_file_and_releases_its_storage_usage(self) -> None:
        asset = self._add_demo_asset()
        path, storage, size = asset.file.name, asset.file.storage, asset.size
        before = OrganizationStorageUsage.objects.get(organization=self.context.organization).bytes_used
        record = self.dataset.records.get(content_type__model="widgetasset", object_id=str(asset.pk))
        with self.captureOnCommitCallbacks(execute=True), tenant_atomic(self.context):
            self.assertTrue(_delete_record(record, set()))
        with tenant_atomic(self.context):
            self.assertFalse(storage.exists(path))
        self.assertFalse(WidgetAsset.objects.exists())
        after = OrganizationStorageUsage.objects.get(organization=self.context.organization).bytes_used
        self.assertEqual(after, before - size)
