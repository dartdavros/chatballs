"""Text stays intact; JSON limits never hide an unreadable history snapshot."""

from django.test import TestCase

from chatballs.ai.external_agents import history
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.conversations.models import Message
from chatballs.tenancy.database import tenant_atomic


class TextBudgetTests(RuntimeData, TestCase):
    def test_oversized_trigger_is_preserved_and_never_dispatched(self):
        text = "я" * 140000
        row = self.request(text)
        self.assertIsNone(self.claim())
        row.refresh_from_db()
        self.assertEqual(row.reason_code, "payload_too_large")
        self.assertEqual(row.attempts, 0)
        self.assertEqual(row.trigger.text, text)

    def test_unpageable_public_history_blocks_dispatch_without_losing_fields(self):
        text = "я" * 140000
        prior = Message.objects.create(conversation=self.conversation, author_type="OPERATOR", text=text)
        row = self.request()
        self.assertIsNone(self.claim())
        row.refresh_from_db()
        self.assertEqual((row.reason_code, row.attempts), ("payload_too_large", 0))
        prior.refresh_from_db()
        self.assertEqual(prior.text, text)
        self.assertEqual(row.snapshot_ciphertext, "")

    def test_large_history_pages_shrink_without_truncating_text(self):
        texts = ["я" * 80000, "ю" * 80000]
        for text in texts:
            Message.objects.create(conversation=self.conversation, author_type="OPERATOR", text=text)
        row = self.request()
        self.assertIsNotNone(self.claim())
        row.refresh_from_db()
        snapshot = open_payload(row.snapshot_ciphertext)
        query = {"authorizationId": str(row.authorization_id),
                 "snapshotCursor": snapshot["context"]["history"]["snapshotCursor"]}
        with tenant_atomic(self.context):
            latest = history.read(self.context, self.connection, self.conversation.pk, query)
            older = history.read(self.context, self.connection, self.conversation.pk,
                                 {**query, "pageCursor": latest["nextCursor"]})
        self.assertEqual(latest["items"][0]["content"]["text"], texts[1])
        self.assertEqual(older["items"][0]["content"]["text"], texts[0])
        self.assertTrue(latest["hasMore"])
        self.assertFalse(older["hasMore"])
