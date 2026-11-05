"""Native reply/fact deliveries use domain writes, receipt and the same wait."""

import hashlib

from chatballs.channels.models import Channel
from chatballs.conversations.domain_events import record_fact
from chatballs.conversations.models import Contact, Conversation, ConversationLabel, Message
from chatballs.events.models import OutboxEvent
from chatballs.integrations.automation_events.callbacks import deliver
from chatballs.integrations.automation_events.native_facts import deliver_fact
from chatballs.integrations.automation_events.replies import accept_reply
from chatballs.integrations.execution import contract_testing
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.tenancy.database import tenant_atomic


class NativeWaitTests(CompositionCase):
    def conversation(self):
        channel = Channel.objects.create(organization=self.organization, code="wait-channel", name="Wait")
        contact = Contact.objects.create(organization=self.organization, name="Wait contact")
        return Conversation.objects.create(organization=self.organization, channel=channel, contact=contact)

    def test_reply_is_scoped_to_conversation_and_outbox_contains_no_text(self):
        with tenant_atomic(self.tenant):
            conversation = self.conversation()
            other = Conversation.objects.create(organization=self.organization, channel=conversation.channel,
                                                contact=conversation.contact)
        run = self.start([{"id": "reply", "kind": "wait", "mode": "reply", "timeout": 3600,
                           "onTimeout": "end"}, self.action("after")], conversation_id=conversation.pk)
        self.pump(run, limit=8)
        for current in (other, conversation):
            with tenant_atomic(self.tenant):
                message = Message.objects.create(conversation=current, author_type="CONTACT", text="private reply")
                fact = OutboxEvent.objects.get(event_type="integrations.reply", payload={"messageId": message.pk})
                self.assertNotIn("private reply", str(fact.payload))
                accept_reply(fact.payload, self.tenant)
                receipt = EventReceipt.objects.get(event_key="conversation.reply", event_id_hash=hashlib.sha256(
                    f"reply:{message.pk}".encode()).hexdigest())
            deliver({"receiptId": receipt.pk}, self.tenant)
            self.pump(run, limit=10)
            self.assertEqual(self.state(run), "pending" if current == other else "completed")
        self.assertEqual(len(contract_testing.CALLS), 1)

    def test_native_facts_are_durable_and_duplicate_delivery_has_one_receipt(self):
        with tenant_atomic(self.tenant):
            conversation = self.conversation()
        run = self.start([{"id": "tag", "kind": "wait", "mode": "event", "connection": "",
            "event": "conversation.tag_added", "condition": {"mode": "all", "items": []},
            "timeout": 3600, "onTimeout": "end"}, self.action("after")], conversation_id=conversation.pk)
        self.pump(run, limit=8)
        with tenant_atomic(self.tenant):
            label = ConversationLabel.objects.create(organization=self.organization, name="Wait label")
            conversation.labels.add(label)
            record_fact(conversation, "CLOSED")
            facts = list(OutboxEvent.objects.filter(event_type="integrations.native_fact"))
            self.assertEqual({row.payload["event"] for row in facts}, {
                "conversation.started", "conversation.closed", "conversation.tag_added"})
            for row in facts:
                deliver_fact(row.payload, self.tenant)
                deliver_fact(row.payload, self.tenant)
            self.assertEqual(EventReceipt.objects.count(), 3)
            receipt = EventReceipt.objects.get(event_key="conversation.tag_added")
        deliver({"receiptId": receipt.pk}, self.tenant)
        self.pump(run)
        self.assertEqual(self.state(run), "completed")
        with tenant_atomic(self.tenant):
            from chatballs.integrations.execution.result_payloads import schema_and_names
            frame = run.progress.get(path="steps/tag")
            spec, _ = schema_and_names(run, frame.definition["block"])
            self.assertIsNotNone(spec)
