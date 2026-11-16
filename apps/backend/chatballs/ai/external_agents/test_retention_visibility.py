"""Delivery truth survives operational retention and fresh authorization."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from chatballs.ai.external_agents import retention
from chatballs.ai.external_agents.context_testing import ContextData
from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.history_payloads import cursor
from chatballs.ai.external_agents.receipt_models import (
    ExternalAgentReceipt,
    ExternalAgentTombstone,
)
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.conversations.control_services import claim_conversation, release_to_ai
from chatballs.conversations.list_queries import conversation_list
from chatballs.conversations.media_queries import visible_message
from chatballs.conversations.message_history import message_history
from chatballs.conversations.message_serializers import message_payload
from chatballs.conversations.models import Message
from chatballs.conversations.selectors import conversation_messages
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat.message_selectors import session_messages


class RetentionVisibilityTests(ContextData, TestCase):
    def interrupted_batch(self):
        row = self.request("first customer turn")
        self.claim()
        result = self.result(row, count=2)
        result["outcome"]["messages"][1]["content"]["text"] = "suppressedsecret"
        self.later_customer = Message.objects.create(conversation=self.conversation, author_type="CONTACT", text="during processing")
        ack, _ = self.accept(row, result)
        self.deliver(times=1)
        claim_conversation(context=self.context, conversation_id=self.conversation.pk)
        self.deliver()
        items = list(ExternalAgentDeliveryItem.objects.select_related("message"))
        self.assertEqual([item.state for item in items], ["transport_accepted", "suppressed"])
        return row, result, ack, items[0].message, items[1].message

    def clean_at(self, instant):
        with tenant_atomic(self.context), patch("chatballs.ai.external_agents.retention.timezone.now", return_value=instant):
            retention.cleanup(self.context)

    def assert_hidden(self, suppressed, accepted):
        self.assertTrue(Message.including_tests.filter(pk=suppressed.pk).exists())
        self.assertFalse(Message.objects.filter(pk=suppressed.pk).exists())
        with self.assertRaises(Message.DoesNotExist):
            visible_message(self.context, suppressed.pk)
        self.assertEqual(conversation_list(self.context, {"q": "suppressedsecret"})["items"], [])
        session = SimpleNamespace(organization_id=self.organization.pk, connection=self.messaging,
            connection_id=self.messaging.pk, identity=SimpleNamespace(contact_id=self.contact.pk))
        self.assertNotIn(suppressed.pk, session_messages(session).values_list("pk", flat=True))
        self.assertNotIn(suppressed.pk, conversation_messages(self.conversation).values_list("pk", flat=True))
        self.assertNotIn(suppressed.pk, [item["id"] for item in message_history(self.conversation, {})["items"]])
        self.assertTrue(Message.objects.filter(pk=accepted.pk).exists())

    def test_payload_and_metadata_boundaries_preserve_visibility_ack_and_delivery_truth(self):
        row, result, ack, accepted, suppressed = self.interrupted_batch()
        ordinary = Message.objects.create(conversation=self.conversation, author_type="OPERATOR", text="ordinary")
        row.refresh_from_db()
        terminal = row.terminal_at
        for age in (timedelta(days=7, microseconds=-1), timedelta(days=7),
                    timedelta(days=30, microseconds=-1), timedelta(days=30)):
            with self.subTest(age=age):
                self.clean_at(terminal + age)
                self.assert_hidden(suppressed, accepted)
                self.assertTrue(Message.objects.filter(pk=ordinary.pk).exists())
                if age < timedelta(days=30):
                    row.refresh_from_db()
                    self.assertEqual(bool(row.snapshot_ciphertext), age < timedelta(days=7))
                    self.assertEqual(bool(ExternalAgentReceipt.objects.get().payload_ciphertext), age < timedelta(days=7))
                else:
                    self.assertFalse(ExternalAgentRequest.objects.exists())
                    self.assertFalse(ExternalAgentDeliveryItem.objects.exists())
                    self.assertFalse(ExternalAgentReceipt.objects.exists())
                    accepted.refresh_from_db()
                    self.assertEqual(message_payload(accepted)["externalDelivery"]["state"], "transport_accepted")
                    suppressed.refresh_from_db()
                    self.assertEqual(message_payload(suppressed)["externalDelivery"]["state"], "suppressed")
        self.assertEqual(ExternalAgentTombstone.objects.count(), 1)
        self.assertEqual(self.accept(row, result)[0], ack)
        self.assertEqual(self.sender.call_count, 1)

    def test_fresh_inline_and_all_history_pages_exclude_suppressed_after_return_and_cleanup(self):
        old, _, _, accepted, suppressed = self.interrupted_batch()
        # Ensure the durable ordering places the old reply before later customer turns.
        later = Message.objects.create(conversation=self.conversation, author_type="CONTACT", text="during takeover")
        prior = [Message.objects.create(conversation=self.conversation, author_type="OPERATOR", text=str(i)) for i in range(25)]
        deleted = prior.pop(2)
        release_to_ai(context=self.context, conversation_id=self.conversation.pk)
        row = self.request("new customer turn")
        future = self.request("future customer turn")
        self.claim()
        window = self.frozen(row)["context"]["history"]
        deleted.delete()
        collected = window["messages"]
        continuation = window["nextCursor"]
        while continuation:
            response = self.client.get(
                f"/api/v1/external-agent/connections/{self.connection.pk}/conversations/{self.conversation.pk}/history/",
                {"authorizationId": str(row.authorization_id), "snapshotCursor": cursor(row),
                 "pageCursor": continuation, "pageSize": 3},
                HTTP_AUTHORIZATION="Bearer " + self.created["incomingKey"])
            self.assertEqual(response.status_code, 200, response.content)
            page = response.json()
            collected = page["items"] + collected
            continuation = page["nextCursor"]
        expected = [old.trigger_id, accepted.pk, self.later_customer.pk, later.pk, *(message.pk for message in prior)]
        self.assertEqual([int(item["id"]) for item in collected], expected)
        self.assertNotIn(suppressed.pk, expected)
        self.assertNotIn(row.trigger_id, expected)
        self.assertNotIn(future.trigger_id, expected)
        old.refresh_from_db()
        self.clean_at(old.terminal_at + timedelta(days=30))
        from chatballs.ai.external_agents.public_messages import history_messages

        self.assertEqual([int(item["id"]) for item in history_messages(row)], expected)

    def test_legacy_unknown_and_suppressed_facts_survive_cleanup_without_resend(self):
        self.sender.return_value = False
        row = self.interrupted_unknown_batch()
        messages = list(Message.including_tests.filter(author_type="AI").order_by("pk"))
        for message in messages:
            # A message from the previous version has no durable delivery fact.
            Message.including_tests.filter(pk=message.pk).update(ai_delivery={"externalFileId": "preserved"})
        row.refresh_from_db()
        self.clean_at(row.terminal_at + timedelta(days=30))
        for message, state in zip(messages, ("unknown", "suppressed"), strict=True):
            message.refresh_from_db()
            self.assertEqual(message_payload(message)["externalDelivery"]["state"], state)
            self.assertEqual(message.ai_delivery["externalFileId"], "preserved")
        self.assertFalse(Message.objects.filter(pk=messages[1].pk).exists())
        self.deliver()
        self.assertEqual(self.sender.call_count, 1)

    def interrupted_unknown_batch(self):
        row = self.request()
        self.claim()
        result = self.result(row, count=2)
        self.accept(row, result)
        self.deliver()
        claim_conversation(context=self.context, conversation_id=self.conversation.pk)
        self.deliver()
        self.assertEqual(list(ExternalAgentDeliveryItem.objects.values_list("state", flat=True)), ["unknown", "suppressed"])
        return row
