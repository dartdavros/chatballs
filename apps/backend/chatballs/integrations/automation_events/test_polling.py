"""Atomic cursor/receipt data and stale-poller fencing on PostgreSQL."""

import uuid
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from chatballs.integrations.adapters.events import PollResult, VerifiedEvent
from chatballs.integrations.automation_events.polling import commit
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.execution.contract_testing import ADAPTER
from chatballs.integrations.scenario_state.automation import PollCursor
from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.tenancy.database import tenant_atomic


class CursorTests(CompositionCase):
    def cursor(self):
        with tenant_atomic(self.tenant):
            row = PollCursor(organization=self.organization, integration=self.integration,
                event_key="job.completed", due_at=timezone.now(), lease_until=timezone.now() + timedelta(seconds=90))
            row.definition = {"cursor": "one"}
            row.save()
            return row

    def response(self):
        return PollResult((VerifiedEvent("poll-id", "job.completed", timezone.now(), {"value": "ready"}),), "two")

    def test_cursor_and_receipt_outbox_are_atomic_and_duplicate_safe(self):
        row, response = self.cursor(), self.response()
        with patch("chatballs.integrations.automation_events.ingress.enqueue_event", side_effect=RuntimeError("commit interrupted")):
            with self.assertRaises(RuntimeError):
                commit(self.tenant, row.pk, str(row.fence), "one", response, ADAPTER.events[0])
        with tenant_atomic(self.tenant):
            row.refresh_from_db()
            self.assertEqual(row.definition["cursor"], "one")
            self.assertFalse(EventReceipt.objects.exists())
        self.assertTrue(commit(self.tenant, row.pk, str(row.fence), "one", response, ADAPTER.events[0]))
        self.assertFalse(commit(self.tenant, row.pk, str(row.fence), "one", response, ADAPTER.events[0]))
        with tenant_atomic(self.tenant):
            row.refresh_from_db()
            self.assertEqual(row.definition["cursor"], "two")
            self.assertEqual(EventReceipt.objects.count(), 1)

    def test_new_lease_and_pause_reject_stale_cursor(self):
        from chatballs.integrations.execution.permissions import ExecutionDenied
        row = self.cursor()
        self.assertFalse(commit(self.tenant, row.pk, str(uuid.uuid4()), "one", self.response(), ADAPTER.events[0]))
        with tenant_atomic(self.tenant):
            self.integration.is_active = False
            self.integration.save(update_fields=["is_active"])
        with self.assertRaisesRegex(ExecutionDenied, "connection_paused"):
            commit(self.tenant, row.pk, str(row.fence), "one", self.response(), ADAPTER.events[0])
        with tenant_atomic(self.tenant):
            self.assertFalse(EventReceipt.objects.exists())
