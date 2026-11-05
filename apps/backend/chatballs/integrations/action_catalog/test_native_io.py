"""Crash injection exercises real file effects without a mock service."""

from unittest.mock import patch

from django.db import connection

from chatballs.integrations.action_catalog.native_file_test_base import NativeFileCase
from chatballs.integrations.execution import native_results
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.models import ServiceFile
from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt
from chatballs.tenancy.database import tenant_atomic


class NativeIORecoveryTests(NativeFileCase):
    def test_crash_before_receipt_leaves_unknown_and_never_blindly_repeats_io(self):
        from chatballs.integrations.action_catalog.testing import execute_action
        with patch.object(native_results, "save", side_effect=RuntimeError("crash-before-receipt")):
            run, _data = execute_action(self.context, "reports.support_csv.get", self.filters())
        self.assertEqual(run.state, "unknown")
        with tenant_atomic(self.context):
            self.assertEqual(ServiceFile.objects.count(), 1)
            self.assertFalse(NativeEffectReceipt.objects.exists())
        control(tenant=self.context, public_id=run.public_id, action="reconcile")
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            run.refresh_from_db()
            self.assertEqual((run.state, ServiceFile.objects.count()), ("unknown", 1))

    def test_receipt_survives_checkpoint_crash_and_replays_files_without_second_export(self):
        from chatballs.integrations.action_catalog.testing import execute_action
        from chatballs.integrations.adapters.files import store_service_file
        from chatballs.integrations.execution.runner import _commit

        def failed_checkpoint(*args, **kwargs):
            if args[2].state == "completed":
                raise RuntimeError("crash-before-checkpoint")
            return _commit(*args, **kwargs)

        def checked_storage(**kwargs):
            self.assertFalse(connection.in_atomic_block)
            return store_service_file(**kwargs)

        with patch("chatballs.integrations.execution.runner._commit", side_effect=failed_checkpoint), \
                patch("chatballs.integrations.adapters.files.store_service_file", side_effect=checked_storage):
            run, _data = execute_action(self.context, "reports.support_csv.get", self.filters())
        self.assertEqual(run.state, "unknown")
        with tenant_atomic(self.context):
            self.assertEqual(NativeEffectReceipt.objects.count(), 1)
            reference = str(ServiceFile.objects.get().public_id)
        control(tenant=self.context, public_id=run.public_id, action="reconcile")
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            run.refresh_from_db()
            self.assertEqual((run.state, ServiceFile.objects.count()), ("completed", 1))
            self.assertEqual(run.steps.get().definition["files"], [reference])
