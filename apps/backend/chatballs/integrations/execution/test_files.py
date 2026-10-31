"""Real temporary filesystem and PostgreSQL ownership, no HTTP service."""

import io
import tempfile
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

from chatballs.integrations.adapters.files import store_service_file
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.retention import cleanup, delete_operation_file
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.execution.test_execution import ExecutionCase
from chatballs.integrations.models import ServiceFile
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


class OperationFileRetentionTests(ExecutionCase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.TemporaryDirectory(prefix=".test-service-retention-", dir=Path(__file__).resolve().parents[3])
        self.addCleanup(self.media.cleanup)
        configuration = override_settings(MEDIA_ROOT=self.media.name)
        configuration.enable()
        self.addCleanup(configuration.disable)

    def source_file(self, *, independent=False):
        run = self.launch()
        run_one(self.tenant, run.public_id, registry=self.registry)
        with tenant_atomic(self.tenant):
            step = run.steps.get()
        reference = store_service_file(context=self.tenant, integration=self.integration, name="result.bin",
            content_type="application/octet-stream", stream=io.BytesIO(b"data"), size=4, step=None if independent else step)
        with tenant_atomic(self.tenant):
            ScenarioRun.objects.filter(pk=run.pk).update(finished_at=timezone.now() - timedelta(days=8))
        return run, reference

    def test_file_is_owned_by_new_active_consumer_and_not_deleted_with_source(self):
        source, reference = self.source_file()
        self.operation = replace(self.operation, input=TypeSpec("object", properties=(("value", TypeSpec("file", required=True)),)))
        self.registry = self.make_registry()
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["steps"][0]["inputs"]["value"]["value"] = {"fileId": reference.file_id}
            self.scenario.definition = document
            self.scenario.save(update_fields=["content"])
        consumer = self.launch(key="consumer", approve=False)
        cleanup(self.tenant)
        with tenant_atomic(self.tenant):
            file = ServiceFile.objects.get(public_id=reference.file_id)
            self.assertTrue(file.execution_owners.filter(step__run=consumer).exists())
            self.assertTrue(file.file.storage.exists(file.file.name))
            self.assertFalse(file.execution_owners.filter(step__run=source).exists())
        control(tenant=self.tenant, public_id=consumer.public_id, action="cancel")
        with tenant_atomic(self.tenant):
            ScenarioRun.objects.filter(pk=consumer.pk).update(finished_at=timezone.now() - timedelta(days=8))
        cleanup(self.tenant)
        with tenant_atomic(self.tenant):
            delete_operation_file({"fileId": reference.file_id}, self.tenant)
            self.assertFalse(ServiceFile.objects.filter(public_id=reference.file_id).exists())

    def test_independent_file_survives_cleanup(self):
        _run, reference = self.source_file(independent=True)
        cleanup(self.tenant)
        with tenant_atomic(self.tenant):
            delete_operation_file({"fileId": reference.file_id}, self.tenant)
            file = ServiceFile.objects.get(public_id=reference.file_id)
            self.assertTrue(file.file.storage.exists(file.file.name))

    def test_storage_failure_keeps_deletion_recoverable_and_retry_is_idempotent(self):
        _run, reference = self.source_file()
        cleanup(self.tenant)
        storage = ServiceFile._meta.get_field("file").storage
        with patch.object(storage, "delete", side_effect=OSError("private remote detail")):
            with self.assertRaisesMessage(RuntimeError, "operation_file_cleanup_failed"), tenant_atomic(self.tenant):
                delete_operation_file({"fileId": reference.file_id}, self.tenant)
        with tenant_atomic(self.tenant):
            file = ServiceFile.objects.get(public_id=reference.file_id)
            name = file.file.name
            self.assertTrue(storage.exists(name))
            delete_operation_file({"fileId": reference.file_id}, self.tenant)
            delete_operation_file({"fileId": reference.file_id}, self.tenant)
            self.assertFalse(storage.exists(name))
