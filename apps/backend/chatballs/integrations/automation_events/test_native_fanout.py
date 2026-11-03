"""Native domain facts retain their transaction and independent subscribers."""

from django.db import transaction

from chatballs.channels.models import Channel
from chatballs.conversations.models import Contact, Conversation, ConversationLabel
from chatballs.events.models import OutboxEvent
from chatballs.integrations.automation_events.configuration import synchronize
from chatballs.integrations.automation_events.fanout import deliver_one
from chatballs.integrations.automation_events.native_facts import deliver_fact
from chatballs.integrations.execution import contract_testing
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.tenancy.database import tenant_atomic


class NativeFanoutTests(CompositionCase):
    def test_domain_rollback_and_duplicate_fact_do_not_duplicate_run(self):
        with tenant_atomic(self.tenant):
            channel = Channel.objects.create(organization=self.organization, code="native-fanout", name="Native")
            contact = Contact.objects.create(organization=self.organization, name="Native")
            conversation = Conversation.objects.create(organization=self.organization, channel=channel, contact=contact)
            label = ConversationLabel.objects.create(organization=self.organization, name="Native")
            document = self.scenario.definition
            document["steps"] = [self.action("run")]
            document["access"]["delegated"] = True
            document["triggers"] = [{"id": "native", "kind": "chatballs", "event": "conversation.tag_added"}]
            self.scenario.definition = document
            self.scenario.save()
            synchronize(self.tenant, self.scenario, {})
            with self.assertRaises(RuntimeError), transaction.atomic():
                conversation.labels.add(label)
                raise RuntimeError("rollback domain operation")
            self.assertFalse(conversation.labels.exists())
            self.assertFalse(OutboxEvent.objects.filter(event_type="integrations.native_fact", payload__event="conversation.tag_added").exists())
            conversation.labels.add(label)
            fact = OutboxEvent.objects.get(event_type="integrations.native_fact", payload__event="conversation.tag_added")
            deliver_fact(fact.payload, self.tenant)
            deliver_fact(fact.payload, self.tenant)
            receipt = EventReceipt.objects.get(event_key="conversation.tag_added")
            self.assertEqual(receipt.deliveries.count(), 1)
            pk = receipt.deliveries.get().pk
        deliver_one(self.tenant, pk, registry=self.registry)
        deliver_one(self.tenant, pk, registry=self.registry)
        with tenant_atomic(self.tenant):
            run = receipt.deliveries.get().run
            self.assertEqual(run.conversation_id, conversation.pk)
        self.pump(run)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(contract_testing.CALLS), 1)
