"""Meaningful text protocol scenarios at real application/outbox boundaries."""

from copy import deepcopy
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.utils import timezone

from chatballs.ai.external_agents.delivery_models import (
    ExternalAgentDelivery,
    ExternalAgentDeliveryItem,
)
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.ai.external_agents.receipt_models import ExternalAgentReceipt
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.conversations.ingest import ingest_inbound
from chatballs.conversations.models import Message
from chatballs.conversations.transports.base import InboundMessage
from chatballs.events.handlers import dispatch as dispatch_event
from chatballs.events.models import OutboxEvent
from chatballs.integrations.adapters.transport import TransportResponse


class RuntimeTests(RuntimeData, TestCase):
    def test_sync_real_inbox_outbox_and_stable_request(self):
        with patch("chatballs.conversations.transports.download_avatar", return_value=None):
            ingest_inbound(self.messaging, InboundMessage(external_id="first", user_id="user",
                           chat_id="inbox-chat", text="Real inbox", display_name="Customer"))
        row = ExternalAgentRequest.objects.get()
        body = self.result(row)
        import json

        self.transport.return_value = TransportResponse(status=200, content_type="application/json", url="",
                                                         body=json.dumps(body).encode())
        event = OutboxEvent.objects.get(event_type="external_agent.wake")
        dispatch_event(event)
        dispatch_event(event)
        row.refresh_from_db()
        self.assertEqual(row.attempts, 1)
        self.assertEqual(ExternalAgentReceipt.objects.count(), 1)
        self.assertEqual(ExternalAgentDelivery.objects.count(), 1)
        self.assertNotIn("Real inbox", row.snapshot_ciphertext)
        with connection.cursor() as cursor:
            cursor.execute("SELECT snapshot_ciphertext FROM ai_externalagentrequest WHERE id=%s", [row.pk])
            self.assertNotIn("Real inbox", cursor.fetchone()[0])
        self.assertFalse(Message.objects.filter(ai_reply_to__isnull=False).exists())
        self.assertFalse(OutboxEvent.objects.filter(event_type="conversation.ai_turn_requested").exists())

    def test_fifo_early_callback_then_202_preserves_receipt_and_context(self):
        first = self.request("first")
        second = self.request("second")
        work = self.claim()
        result = self.result(first)
        response = self.callback(first, result)
        self.assertEqual(response.status_code, 202, response.content)
        self.settle(work, {"version": "1", "requestId": str(first.public_id), "status": "accepted", "externalSessionId": "session-1"}, 202)
        self.assertIsNone(self.claim())
        self.deliver()
        next_work = self.claim()
        self.assertEqual(next_work.request_id, str(second.public_id))
        second.refresh_from_db()
        snapshot = open_payload(second.snapshot_ciphertext)
        self.assertEqual([item["content"]["text"] for item in snapshot["context"]["history"]["messages"]], ["first", "Answer"])
        self.assertEqual(snapshot["trigger"]["text"], "second")
        self.assertEqual(snapshot["conversation"]["externalSessionId"], "session-1")

    def test_callback_repeat_exact_ack_conflicts_and_current_delivery_scope(self):
        row = self.request()
        self.claim()
        result = self.result(row, count=2)
        ack = self.callback(row, result)
        self.assertEqual(ack.status_code, 202, ack.content)
        self.deliver(times=3)
        repeat = self.callback(row, result)
        self.assertEqual(repeat.status_code, 200)
        self.assertEqual(repeat.json(), ack.json())
        self.assertEqual(ExternalAgentDeliveryItem.objects.count(), 2)
        for key in ("resultId", "externalSessionId"):
            changed = deepcopy(result)
            changed[key] = "00000000-0000-0000-0000-000000000001" if key == "resultId" else "other-session"
            self.assertEqual(self.callback(row, changed).status_code, 409)
        changed = deepcopy(result)
        changed["outcome"]["messages"][0]["content"]["text"] = "Changed"
        self.assertEqual(self.callback(row, changed).status_code, 409)
        url = f"/api/v1/external-agent/connections/{self.connection.pk}/deliveries/{ack.json()['deliveryId']}/"
        header = {"HTTP_AUTHORIZATION": "Bearer " + self.created["incomingKey"]}
        self.assertEqual(self.client.get(url, **header).status_code, 404)
        scoped = self.client.get(url, {"authorizationId": str(row.authorization_id)}, **header)
        self.assertEqual(scoped.status_code, 200, scoped.content)
        self.assertEqual(scoped.json()["state"], "transport_accepted")
        self.assertEqual(self.sender.call_count, 2)

    def test_202_releases_job_but_not_fifo_polls_without_repost(self):
        row = self.request()
        self.request("later")
        work = self.claim()
        accepted = {"version": "1", "requestId": str(row.public_id), "status": "accepted", "externalSessionId": None}
        row.refresh_from_db()
        self.assertIsNotNone(work, (row.state, row.reason_code))
        before = timezone.now()
        self.settle(work, accepted, 202)
        row.refresh_from_db()
        self.assertEqual(row.state, "accepted")
        self.assertIsNone(row.lease_until)
        self.assertAlmostEqual((row.next_at - before).total_seconds(), 5, delta=2)
        self.assertIsNone(self.claim())
        ExternalAgentRequest.objects.filter(pk=row.pk).update(next_at=timezone.now())
        poll = self.claim()
        self.assertEqual(poll.request.method, "GET")
        self.settle(poll, {**accepted, "status": "processing"})
        row.refresh_from_db()
        self.assertEqual(row.attempts, 1)
        self.assertEqual(row.polls, 1)
        self.assertAlmostEqual((row.next_at - timezone.now()).total_seconds(), 15, delta=2)

    def test_failed_and_handoff_never_make_public_summary_or_delivery(self):
        for failed in (True, False):
            with self.subTest(failed=failed):
                self.conversation.control_mode = "AI"
                self.conversation.save(update_fields=["control_mode"])
                row = self.request()
                self.claim()
                result = self.result(row)
                if failed:
                    result.pop("outcome")
                    result.pop("externalSessionId")
                    result.update(status="failed", error={"code": "service_failed", "retryable": False})
                else:
                    result["outcome"] = {"type": "handoff", "reasonCode": "cannot_answer", "summary": "Private summary"}
                ack, status = self.accept(row, result)
                self.assertEqual((ack["state"], status), ("failed" if failed else "handed_off", 200))
                self.assertIsNone(ack["deliveryId"])
                self.assertFalse(ExternalAgentDelivery.objects.exists())
                self.assertFalse(Message.objects.filter(author_type="AI").exists())
                self.conversation.refresh_from_db()
                self.assertEqual(self.conversation.control_mode, "PAUSED")
                self.assertEqual(self.accept(row, result)[0], ack)
                from chatballs.notifications.models import Notification

                notification = Notification.objects.get(dedup_key=f"external-handoff:{row.public_id}")
                self.assertEqual(notification.audience, "OPERATORS")
                self.assertEqual(notification.audience_group_id, self.conversation.group_id)
                self.assertEqual(notification.body, "" if failed else "Private summary")

    def test_plain_handoff_token_is_text_and_unsupported_context_is_not_dispatched(self):
        from chatballs.ai.runtime import HANDOFF_TOKEN

        row = self.request()
        self.claim()
        self.accept(row, self.result(row, text=HANDOFF_TOKEN))
        self.deliver()
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.control_mode, "AI")
        self.assertTrue(Message.objects.filter(author_type="AI", text=HANDOFF_TOKEN).exists())
        self.bind(self.connection.pk, standardFields=["name"])
        unsupported = self.request("Needs extended context")
        self.assertIsNotNone(self.claim())
        unsupported.refresh_from_db()
        self.assertEqual(open_payload(unsupported.snapshot_ciphertext)["context"]["customer"]["fields"], {"name": "Customer"})
        self.assertEqual(unsupported.attempts, 1)
