"""Signed callback receipts and persistent decisions use the real PostgreSQL."""

import hashlib
import hmac
import json
from dataclasses import replace
from datetime import timedelta

from django.utils import timezone

from chatballs.events.models import OutboxEvent
from chatballs.integrations.adapters.contracts import OperationHandlers
from chatballs.integrations.automation_events.callbacks import deliver
from chatballs.integrations.automation_events.ingress import receive
from chatballs.integrations.execution import contract_testing
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.wait_controls import decide, decision_digest
from chatballs.tenancy.database import tenant_atomic


class CallbackTests(CompositionCase):
    def send(self, identity="event-1", *, value="ready", connection=None, correlation="", sequence=1, state=None, secret="test-signature"):
        body = json.dumps({"id": identity, "event": "job.completed", "time": timezone.now().isoformat(),
            "payload": {"value": value}, "correlation": correlation, "sequence": sequence,
            **({"state": state} if state else {})}).encode()
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return receive(self.tenant, (connection or self.integration).pk, "job.completed", body,
                       {"X-Signature": signature}, registry=self.registry)

    def wait_event(self):
        return {"id": "event", "kind": "wait", "mode": "event",
                "connection": str(self.integration.pk), "event": "job.completed",
                "condition": {"mode": "all", "items": [{"left": {"source": "event", "path": "value"},
                    "op": "eq", "right": {"source": "constant", "value": "ready"}}]},
                "timeout": 3600, "onTimeout": "end"}

    def test_callback_before_registration_duplicate_and_conflicting_id(self):
        run = self.start([self.wait_event(), self.action("after")])
        receipt, created = self.send()
        self.assertTrue(created)
        self.pump(run)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(contract_testing.CALLS), 1)
        # Duplicate byte-independent envelope has the same semantic payload.
        with tenant_atomic(self.tenant):
            self.assertEqual(run.waits.get().receipt_id, receipt.pk)
            self.assertNotIn("ready", receipt.content)
            self.assertTrue(OutboxEvent.objects.filter(event_type="integrations.receipt", payload={"receiptId": receipt.pk}).exists())
        same, created = self.send()
        self.assertFalse(created)
        self.assertEqual(same.pk, receipt.pk)
        with self.assertRaisesRegex(ExecutionDenied, "event_conflict"):
            self.send(value="changed")
        deliver({"receiptId": receipt.pk}, self.tenant)
        self.pump(run)
        self.assertEqual(len(contract_testing.CALLS), 1)

    def test_bad_signature_and_other_connection_cannot_resume(self):
        run = self.start([self.wait_event(), self.action("after")])
        with self.assertRaisesRegex(ExecutionDenied, "event_invalid"):
            self.send(secret="wrong")
        receipt, _ = self.send(connection=self.other_connection, secret="other-signature")
        self.pump(run, limit=10)
        deliver({"receiptId": receipt.pk}, self.tenant)
        self.pump(run, limit=2)
        self.assertEqual(self.state(run), "pending")
        self.assertEqual(contract_testing.CALLS, [])

    def test_valid_signature_cannot_cross_the_organization_boundary(self):
        from chatballs.integrations.models import Integration
        from chatballs.integrations.scenario_state.receipts import EventReceipt
        from chatballs.tenancy.context import TenantContext
        foreign = TenantContext.for_resource(self.other)
        def attempt():
            with self.assertRaises(Integration.DoesNotExist):
                receive(foreign, self.integration.pk, "job.completed", b"{}", {}, registry=self.registry)
            with tenant_atomic(foreign):
                self.assertFalse(EventReceipt.objects.exists())
        self.as_runtime(attempt)

    def test_long_result_duplicate_and_older_sequence_do_not_repeat_effect(self):
        run = self.start([self.action("job", operation="job"), self.action("after")])
        self.pump(run, limit=12)
        with tenant_atomic(self.tenant):
            step = run.steps.get(path="steps/job")
            key = str(step.effect_key)
            self.assertEqual(step.state, "waiting")
        receipt, _ = self.send(correlation=key, state="completed", sequence=2)
        deliver({"receiptId": receipt.pk}, self.tenant)
        self.pump(run)
        self.assertEqual(self.state(run), "completed")
        older, _ = self.send("older", correlation=key, state="failed", value="failed", sequence=1)
        deliver({"receiptId": older.pk}, self.tenant)
        self.pump(run, limit=2)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(contract_testing.CALLS), 2)

    def test_confirmation_digest_deadline_and_duplicate_decision(self):
        run = self.start([{"id": "decision", "kind": "wait", "mode": "confirmation",
                          "approver": "initiator", "timeout": 3600, "onTimeout": "end"}, self.action("after")])
        self.pump(run)
        with tenant_atomic(self.tenant):
            row = run.waits.get()
            token = decision_digest(row)
            generation = str(row.generation)
        with self.assertRaisesRegex(ExecutionDenied, "approval_changed"):
            decide(self.tenant, run.public_id, path=row.path, generation=generation, digest="changed", accepted=True)
        decide(self.tenant, run.public_id, path=row.path, generation=generation, digest=token, accepted=True)
        with self.assertRaisesRegex(ExecutionDenied, "approval_changed"):
            decide(self.tenant, run.public_id, path=row.path, generation=generation, digest=token, accepted=True)
        self.pump(run)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(contract_testing.CALLS), 1)

    def test_callback_inside_execute_is_durable_before_wait_registration(self):
        def early(context, operation, arguments):
            self.send("higher", correlation=context.effect_key, state="completed", sequence=2)
            self.send("lower", correlation=context.effect_key, state="failed", sequence=1)
            return contract_testing.pending(context, operation, arguments)
        registry = self.registry
        original = registry.adapter("independent")
        from chatballs.integrations.adapters.registry import build_registry
        self.registry = build_registry([])
        operations = tuple(replace(op, handlers=OperationHandlers(execute=early, resume=contract_testing.resume))
                           if op.key == "job" else op for op in original.operations)
        self.registry.register_adapter(replace(original, operations=operations))
        run = self.start([self.action("job", operation="job"), self.action("after")])
        self.pump(run)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(contract_testing.CALLS), 2)
        with tenant_atomic(self.tenant):
            self.assertEqual(run.waits.get().receipt.sequence, 2)

    def test_receipt_and_outbox_rollback_before_ack(self):
        from unittest.mock import patch

        from chatballs.integrations.scenario_state.receipts import EventReceipt
        with patch("chatballs.integrations.automation_events.ingress.enqueue_event", side_effect=RuntimeError("commit failed")):
            with self.assertRaises(RuntimeError):
                self.send()
        with tenant_atomic(self.tenant):
            self.assertEqual(EventReceipt.objects.count(), 0)

    def test_deadline_wins_and_late_confirmation_is_rejected(self):
        run = self.start([{"id": "decision", "kind": "wait", "mode": "confirmation", "timeout": 3600,
                          "approver": "initiator", "onTimeout": "end"}, self.action("never")])
        self.pump(run)
        with tenant_atomic(self.tenant):
            row = run.waits.get()
            generation, token = str(row.generation), decision_digest(row)
            run.waits.update(deadline=timezone.now() - timedelta(seconds=1))
        with self.assertRaisesRegex(ExecutionDenied, "approval_changed"):
            decide(self.tenant, run.public_id, path=row.path, generation=generation, digest=token, accepted=True)
        self.pump(run)
        self.assertEqual(self.state(run), "cancelled")
        self.assertEqual(contract_testing.CALLS, [])
