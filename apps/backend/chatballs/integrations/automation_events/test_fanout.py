"""Durable subscribers execute through the same real PostgreSQL runner."""

from unittest.mock import patch

from django.db import transaction
from django.utils import timezone

from chatballs.events.models import OutboxEvent
from chatballs.integrations.adapters.events import VerifiedEvent
from chatballs.integrations.automation_events.configuration import synchronize
from chatballs.integrations.automation_events.fanout import deliver, deliver_one
from chatballs.integrations.automation_events.ingress import persist
from chatballs.integrations.execution import contract_testing
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.scenario_state.automation import EventDelivery
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


class FanoutTests(CompositionCase):
    def subscribe(self, name="Subscriber", *, delegated=True):
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["steps"] = [self.action("project", {"source": "event", "path": "value"})]
            document["triggers"] = [{"id": "event", "kind": "service", "connection": str(self.integration.pk), "event": "job.completed"}]
            document["access"]["delegated"] = delegated
            row = ScenarioDefinition(organization=self.organization, name=name, enabled=True)
            row.definition = document
            row.save()
            synchronize(self.tenant, row, {})
            return row

    def receipt(self, identity="receipt"):
        return persist(self.tenant, self.integration.pk, VerifiedEvent(identity, "job.completed", timezone.now(), {"value": "private"}), replay_seconds=86400)[0]

    def test_audience_and_run_identity_survive_revision_and_redelivery(self):
        scenario = self.subscribe()
        receipt = self.receipt()
        self.subscribe("Later subscription")
        with tenant_atomic(self.tenant):
            self.assertEqual(receipt.deliveries.count(), 1)
            self.assertTrue(OutboxEvent.objects.filter(event_type="integrations.fanout").exists())
            pk = receipt.deliveries.get().pk
        deliver_one(self.tenant, pk, registry=self.registry)
        with tenant_atomic(self.tenant):
            delivery = EventDelivery.objects.get(pk=pk)
            run = delivery.run
            scenario.revision += 1
            scenario.save(update_fields=["revision"])
        deliver_one(self.tenant, pk, registry=self.registry)
        self.pump(run)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(contract_testing.CALLS), 1)
        with tenant_atomic(self.tenant):
            self.assertEqual(ScenarioRun.objects.filter(scenario=scenario).count(), 1)
            self.assertEqual(run.definition["triggerKind"], "service")
            self.assertNotIn("private", run.content)

    def test_partial_distribution_recovers_without_losing_other_subscribers(self):
        self.subscribe("First")
        self.subscribe("Second")
        receipt = self.receipt()
        original = deliver_one
        calls = []
        def crash(tenant, pk):
            calls.append(pk)
            if len(calls) == 1:
                original(tenant, pk, registry=self.registry)
                raise RuntimeError("after commit")
            original(tenant, pk, registry=self.registry)
        with patch("chatballs.integrations.automation_events.fanout.deliver_one", side_effect=crash):
            with self.assertRaises(RuntimeError):
                deliver({"receiptId": receipt.pk}, self.tenant)
        deliver({"receiptId": receipt.pk}, self.tenant)
        with tenant_atomic(self.tenant):
            self.assertEqual(receipt.deliveries.filter(state="delivered").count(), 2)
            runs = list(ScenarioRun.objects.all())
        for run in runs:
            self.pump(run)
        self.assertEqual(len(contract_testing.CALLS), 2)

    def test_receipt_audience_and_outbox_rollback_together(self):
        self.subscribe()
        with tenant_atomic(self.tenant):
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    self.receipt()
                    raise RuntimeError("rollback")
            self.assertFalse(EventDelivery.objects.exists())
            self.assertFalse(OutboxEvent.objects.filter(event_type="integrations.fanout").exists())

    def test_delegation_revocation_blocks_new_effect(self):
        scenario = self.subscribe()
        receipt = self.receipt()
        with tenant_atomic(self.tenant):
            pk = receipt.deliveries.get().pk
        deliver_one(self.tenant, pk, registry=self.registry)
        with tenant_atomic(self.tenant):
            run = EventDelivery.objects.get(pk=pk).run
            document = scenario.definition
            document["access"]["delegated"] = False
            scenario.definition = document
            scenario.save()
        self.pump(run)
        self.assertEqual(self.state(run), "failed")
        self.assertEqual(contract_testing.CALLS, [])

    def test_watchdog_resumes_due_failed_delivery_after_connection_pause(self):
        from datetime import timedelta

        from chatballs.integrations.automation_events.fanout import tick
        from chatballs.integrations.models import Integration

        self.subscribe()
        receipt = self.receipt()
        with tenant_atomic(self.tenant):
            pk = receipt.deliveries.get().pk
            Integration.objects.filter(pk=self.integration.pk).update(is_active=False)
        deliver_one(self.tenant, pk, registry=self.registry)
        with tenant_atomic(self.tenant):
            row = EventDelivery.objects.get(pk=pk)
            self.assertEqual(row.state, "pending")
            self.assertTrue(row.error_code)
            Integration.objects.filter(pk=self.integration.pk).update(is_active=True)
            EventDelivery.objects.filter(pk=pk).update(due_at=timezone.now() - timedelta(seconds=1))
        tick(self.tenant)
        deliver_one(self.tenant, pk, registry=self.registry)
        with tenant_atomic(self.tenant):
            row.refresh_from_db()
            self.assertEqual(row.state, "delivered")
            self.assertIsNone(row.lease_until)
