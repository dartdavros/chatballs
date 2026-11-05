"""Real domain files, export formats and tenant/step ownership through runner."""

import tempfile
from datetime import timedelta
from pathlib import Path

from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from chatballs.conversations.domain_event_test_base import DomainEventTestBase
from chatballs.integrations.adapters.file_access import file_opener
from chatballs.integrations.models import ServiceFile
from chatballs.tenancy.database import tenant_atomic


class NativeFileCase(TransactionTestCase):
    def setUp(self):
        DomainEventTestBase.setUpTestData.__func__(type(self))
        media = tempfile.TemporaryDirectory(prefix=".test-native-files-", dir=Path(__file__).resolve().parents[3])
        self.addCleanup(media.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media.name))

    def filters(self):
        return {"from": (self.conversation.created_at - timedelta(seconds=1)).isoformat(),
            "to": (timezone.now() + timedelta(seconds=1)).isoformat(), "timezone": "UTC"}

    def read_result(self, run, result):
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        with tenant_atomic(self.context):
            record = ServiceFile.objects.get(public_id=result["file"]["fileId"])
            self.assertIsNone(record.integration_id)
            self.assertFalse(record.independent_owner)
            self.assertTrue(record.execution_owners.filter(step__run=run).exists())
            self.assertIn("/service-files/native/", record.file.name)
            return file_opener(self.organization.pk)(str(record.public_id))
