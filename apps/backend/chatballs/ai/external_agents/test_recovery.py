"""Restart, fencing, cancellation and retention at isolated durable boundaries."""

from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from chatballs.ai.external_agents import delivery, dispatch, retention
from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.ai.external_agents.receipt_models import ExternalAgentReceipt, ExternalAgentTombstone
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.conversations.models import Message
from chatballs.tenancy.database import tenant_atomic


class RecoveryTests(RuntimeData, TestCase):
    def test_retry_schedule_exhaustion_and_best_effort_cancel_keep_original_id(self):
        row = self.request()
        original = None
        for attempt, delay in enumerate((1, 5, 15, 0), 1):
            work = self.claim()
            self.assertIsNotNone(work)
            original = original or work.request.body
            self.assertEqual(work.request.body, original)
            self.settle(work)
            row.refresh_from_db()
            self.assertEqual(row.attempts, attempt)
            self.assertAlmostEqual((row.next_at - timezone.now()).total_seconds(), delay, delta=1)
            ExternalAgentRequest.objects.filter(pk=row.pk).update(next_at=timezone.now())
        self.assertIsNone(self.claim())
        row.refresh_from_db()
        self.assertEqual(row.state, "cancelled")
        dispatch.run(self.context, self.conversation.pk)
        cancel_request = self.transport.call_args.args[0]
        self.assertTrue(cancel_request.url.endswith(f"/requests/{row.public_id}/cancel"))
        self.assertEqual(self.callback(row, self.result(row)).json()["state"], "suppressed")
        self.assertFalse(Message.objects.filter(author_type="AI").exists())

    def test_explicit_long_policy_freezes_configured_deadline_without_24h_ceiling(self):
        self.bind(self.connection.pk, processingMode="long", ordinaryTimeout=120,
                  longTimeout=172800, maximumTimeout=259200)
        row = self.request()
        self.assertEqual((row.deadline_at - row.trigger.created_at).total_seconds(), 172800)
        work = self.claim()
        self.settle(work, {"version": "1", "requestId": str(row.public_id), "status": "accepted", "externalSessionId": None}, 202)
        row.refresh_from_db()
        self.assertEqual((row.deadline_at - row.trigger.created_at).total_seconds(), 172800)

    def test_lost_response_retries_same_snapshot_and_fences_old_worker(self):
        row = self.request()
        first = self.claim()
        self.settle(first)
        row.refresh_from_db()
        self.assertAlmostEqual((row.next_at - timezone.now()).total_seconds(), 1, delta=1)
        self.assertIsNone(self.claim())
        ExternalAgentRequest.objects.filter(pk=row.pk).update(next_at=timezone.now())
        second = self.claim()
        self.assertEqual(first.request.body, second.request.body)
        self.assertEqual(first.request_id, second.request_id)
        self.assertGreater(second.fence, first.fence)
        self.settle(first, self.result(row))
        self.assertFalse(ExternalAgentReceipt.objects.exists())
        self.settle(second, self.result(row))
        self.assertEqual(ExternalAgentReceipt.objects.count(), 1)

    def test_restart_after_claim_uses_same_id_and_payload(self):
        row = self.request()
        first = self.claim()
        ExternalAgentRequest.objects.filter(pk=row.pk).update(lease_until=timezone.now() - timedelta(seconds=1))
        second = self.claim()
        self.assertEqual(first.request.body, second.request.body)
        self.assertEqual(first.request_id, second.request_id)
        self.assertEqual(second.fence, first.fence + 1)

    def test_deadline_does_not_extend_and_late_result_is_suppressed(self):
        row = self.request()
        work = self.claim()
        deadline = row.deadline_at
        accepted = {"version": "1", "requestId": str(row.public_id), "status": "accepted", "externalSessionId": None}
        self.settle(work, accepted, 202)
        row.refresh_from_db()
        with patch("chatballs.ai.external_agents.dispatch.timezone.now", return_value=deadline + timedelta(seconds=1)):
            self.assertIsNone(self.claim())
        row.refresh_from_db()
        self.assertEqual(row.deadline_at, deadline)
        self.assertEqual(row.state, "cancelled")
        self.assertEqual(row.reason_code, "deadline_exceeded")
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.control_mode, "PAUSED")
        late = self.callback(row, self.result(row))
        self.assertEqual(late.status_code, 200, late.content)
        self.assertEqual(late.json()["state"], "suppressed")
        self.assertFalse(Message.objects.filter(author_type="AI").exists())

    def test_unknown_delivery_is_neither_retried_nor_overtaken(self):
        first = self.request()
        self.request("second")
        self.claim()
        self.accept(first, self.result(first, count=2))
        self.sender.return_value = False
        self.deliver(times=3)
        states = list(ExternalAgentDeliveryItem.objects.values_list("state", flat=True))
        self.assertEqual(states, ["unknown", "queued"])
        self.assertEqual(self.sender.call_count, 1)
        self.assertIsNone(self.claim())
        first.refresh_from_db()
        self.assertTrue(first.active)
        self.conversation.control_mode = "HUMAN"
        self.conversation.save(update_fields=["control_mode"])
        self.deliver()
        self.assertEqual(list(ExternalAgentDeliveryItem.objects.values_list("state", flat=True)), ["unknown", "suppressed"])
        self.assertEqual(self.sender.call_count, 1)

    def test_restart_after_channel_handoff_is_unknown_without_resend(self):
        row = self.request()
        self.claim()
        self.accept(row, self.result(row))
        with tenant_atomic(self.context):
            self.assertIsNotNone(delivery.claim(self.context, self.conversation.pk))
        self.deliver()
        self.sender.assert_not_called()
        self.assertEqual(ExternalAgentDeliveryItem.objects.get().state, "unknown")

    def test_retention_protects_active_payload_preserves_tombstone_and_exact_ack(self):
        row = self.request()
        self.claim()
        result = self.result(row)
        ack, _ = self.accept(row, result)
        with tenant_atomic(self.context), patch("chatballs.ai.external_agents.retention.timezone.now", return_value=timezone.now() + timedelta(days=40)):
            retention.cleanup(self.context)
        row.refresh_from_db()
        self.assertTrue(row.snapshot_ciphertext)
        self.deliver()
        with tenant_atomic(self.context), patch("chatballs.ai.external_agents.retention.timezone.now", return_value=timezone.now() + timedelta(days=8)):
            retention.cleanup(self.context)
        row.refresh_from_db()
        self.assertEqual(row.snapshot_ciphertext, "")
        self.assertEqual(ExternalAgentReceipt.objects.get().payload_ciphertext, "")
        self.assertEqual(self.accept(row, result)[0], ack)
        with tenant_atomic(self.context), patch("chatballs.ai.external_agents.retention.timezone.now", return_value=timezone.now() + timedelta(days=31)):
            retention.cleanup(self.context)
        self.assertFalse(ExternalAgentRequest.objects.exists())
        self.assertEqual(ExternalAgentTombstone.objects.count(), 1)
        self.assertEqual(self.accept(row, result)[0], ack)
        from chatballs.conversations.ai_turn_state import request_ai_turn

        with tenant_atomic(self.context):
            request_ai_turn(message=row.trigger, user_id="test-user", context=self.context)
        self.assertFalse(ExternalAgentRequest.objects.exists())

    def test_archive_clears_operational_payload_and_deleted_dialog_cannot_revive(self):
        row = self.request()
        self.claim()
        result = self.result(row)
        self.conversation.archived_at = timezone.now()
        self.conversation.save(update_fields=["archived_at"])
        row.refresh_from_db()
        self.assertFalse(row.active)
        self.assertEqual(row.snapshot_ciphertext, "")
        self.assertEqual(self.callback(row, result).json()["state"], "suppressed")
        self.assertEqual(ExternalAgentReceipt.objects.get().payload_ciphertext, "")
        self.assertEqual(len(ExternalAgentTombstone.objects.get().trigger_digest), 64)
        self.conversation.delete()
        self.assertFalse(ExternalAgentRequest.objects.exists())
        self.assertEqual(self.callback(row, result).json()["state"], "suppressed")
        self.assertEqual(ExternalAgentTombstone.objects.count(), 1)

    def test_database_rejects_snapshot_identity_and_receipt_mutation(self):
        row = self.request()
        self.claim()
        row.refresh_from_db()
        self.assertEqual(open_payload(row.snapshot_ciphertext)["trigger"]["text"], "Question")
        for change in ({"snapshot_ciphertext": "replacement"}, {"deadline_at": timezone.now()}, {"seed_ciphertext": ""}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                ExternalAgentRequest.objects.filter(pk=row.pk).update(**change)
        self.accept(row, self.result(row))
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExternalAgentReceipt.objects.update(digest="0" * 64)
