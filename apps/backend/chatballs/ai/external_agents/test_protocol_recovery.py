"""Unknown status, capped scheduling and immutable terminal cancellation."""

import http.client
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from chatballs.ai.external_agents import dispatch, recovery
from chatballs.ai.external_agents.receipt_models import ExternalAgentReceipt
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.ai.external_agents.state import cancel
from chatballs.integrations.adapters.transport import TransportResponse
from chatballs.tenancy.database import tenant_atomic


class ProtocolRecoveryTests(RuntimeData, TestCase):
    def test_post_framing_failure_keeps_id_and_uses_transport_retry(self):
        row = self.request()
        self.transport.side_effect = http.client.BadStatusLine("test-only malformed response")
        dispatch.run(self.context, self.conversation.pk)
        row.refresh_from_db()
        self.assertEqual((row.attempts, row.state), (1, "dispatching"))
        self.assertAlmostEqual((row.next_at - timezone.now()).total_seconds(), 1, delta=1)
        self.assertIsNone(row.lease_until)
        self.assertFalse(ExternalAgentReceipt.objects.exists())
        self.assertEqual(self.transport.call_args.args[0].headers["Idempotency-Key"], str(row.public_id))
        with tenant_atomic(self.context):
            cancel(row, self.context, "control_revoked")
        recovery.cancel_due(self.context, self.conversation.pk)
        row.refresh_from_db()
        self.assertEqual(row.state, "cancelled")
        self.assertFalse(row.cancel_pending)
        self.assertTrue(self.transport.call_args.args[0].url.endswith("/cancel"))

    def test_unknown_uses_only_status_until_terminal_without_new_deadline(self):
        row = self.request()
        self.assertEqual((row.deadline_at - row.trigger.created_at).total_seconds(), 120)
        work = self.claim()
        unknown = {"version": "1", "requestId": str(row.public_id), "status": "unknown",
                   "externalSessionId": None, "reasonCode": "service_failed"}
        self.settle(work, unknown, 202)
        for delay in (15, 30, 30):
            ExternalAgentRequest.objects.filter(pk=row.pk).update(next_at=timezone.now())
            poll = self.claim()
            self.assertEqual(poll.request.method, "GET")
            self.settle(poll, unknown)
            row.refresh_from_db()
            self.assertEqual(row.attempts, 1)
            self.assertAlmostEqual((row.next_at - timezone.now()).total_seconds(), delay, delta=2)
        self.assertFalse(ExternalAgentReceipt.objects.exists())
        original_deadline = row.deadline_at
        ExternalAgentRequest.objects.filter(pk=row.pk).update(next_at=timezone.now())
        self.settle(self.claim(), self.result(row))
        row.refresh_from_db()
        self.assertEqual(row.deadline_at, original_deadline)
        self.assertEqual(row.state, "delivering")

    def test_retry_after_cannot_extend_deadline(self):
        row = self.request()
        work = self.claim()
        response = TransportResponse(status=503, content_type="application/json", url="",
                                     headers={"retry-after": "9" * 100})
        with tenant_atomic(self.context):
            dispatch.settle(work, self.context, response)
        row.refresh_from_db()
        self.assertEqual(row.next_at, row.deadline_at)
        with patch("chatballs.ai.external_agents.dispatch.timezone.now", return_value=row.deadline_at + timedelta(seconds=1)):
            self.assertIsNone(self.claim())

    def test_cancel_keeps_completed_receipt_and_disabled_feature_sends_nothing(self):
        row = self.request()
        self.claim()
        result = self.result(row)
        ack, _ = self.accept(row, result)
        self.deliver()
        row.refresh_from_db()
        with tenant_atomic(self.context):
            cancel(row, self.context, "control_revoked")
        self.assertEqual(self.accept(row, result)[0], ack)
        row.refresh_from_db()
        self.assertEqual(row.state, "terminal")
        # A pending cancellation is discarded locally after the capability is off.
        ExternalAgentRequest.objects.filter(pk=row.pk).update(cancel_pending=True)
        self.client.patch(self.url, {"enabled": False}, format="json")
        self.transport.reset_mock()
        recovery.cancel_due(self.context, self.conversation.pk)
        self.transport.assert_not_called()
