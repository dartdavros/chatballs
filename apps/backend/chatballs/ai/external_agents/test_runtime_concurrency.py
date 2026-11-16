"""Real PostgreSQL races and tenant roles; HTTP boundaries stay in-process."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TransactionTestCase

from chatballs.ai.external_agents import dispatch
from chatballs.ai.external_agents.delivery_models import (
    ExternalAgentDelivery,
    ExternalAgentDeliveryItem,
)
from chatballs.ai.external_agents.receipt_models import ExternalAgentReceipt, ExternalAgentTombstone
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.ai.external_agents.send_guards import delivery_handoff
from chatballs.conversations.models import Conversation
from chatballs.identity.models import Organization
from chatballs.integrations.adapters.transport import TransportResponse
from chatballs.tenancy.database import tenant_atomic


class RuntimeConcurrencyTests(RuntimeData, TransactionTestCase):
    def concurrent(self, function):
        barrier = Barrier(2)

        def run():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return function()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run) for _ in range(2)]
            return [future.result(timeout=30) for future in futures]

    def test_two_workers_claim_only_one_head(self):
        first = self.request()
        self.request("next")
        works = self.concurrent(self.claim)
        claimed = [work for work in works if work is not None]
        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0].request_id, str(first.public_id))
        self.assertEqual(ExternalAgentRequest.objects.filter(active=True).count(), 1)

    def test_two_callbacks_commit_one_receipt_delivery_and_message(self):
        row = self.request()
        self.claim()
        result = self.result(row)
        acknowledgements = self.concurrent(lambda: self.accept(row, result))
        self.assertEqual(sorted(status for _, status in acknowledgements), [200, 202])
        self.assertEqual(acknowledgements[0][0], acknowledgements[1][0])
        self.assertEqual(ExternalAgentReceipt.objects.count(), 1)
        self.assertEqual(ExternalAgentDelivery.objects.count(), 1)
        self.assertEqual(ExternalAgentDeliveryItem.objects.count(), 1)

    def test_network_boundaries_have_no_transaction_and_callback_may_win_post(self):
        row = self.request()
        result = self.result(row)

        def http(request, *, limits):
            self.assertFalse(connection.in_atomic_block)
            self.assertEqual(limits.timeout_seconds, 10)
            self.assertEqual(request.headers["Idempotency-Key"], str(row.public_id))
            self.accept(row, result)
            accepted = {"version": "1", "requestId": str(row.public_id), "status": "accepted", "externalSessionId": "session-1"}
            return TransportResponse(status=202, content_type="application/json", url="", body=json.dumps(accepted).encode())

        self.transport.side_effect = http
        dispatch.run(self.context, self.conversation.pk)
        self.assertEqual(ExternalAgentReceipt.objects.count(), 1)

        def channel(*args, **kwargs):
            self.assertFalse(connection.in_atomic_block)
            return True

        self.sender.side_effect = channel
        self.deliver()
        self.assertEqual(ExternalAgentDeliveryItem.objects.get().state, "transport_accepted")

    def test_all_runtime_tables_are_hidden_by_rls_outside_tenant(self):
        row = self.request()
        self.claim()
        self.accept(row, self.result(row))
        other = Organization.objects.create(name="Other", slug="runtime-other")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExternalAgentDelivery.objects.bulk_create([ExternalAgentDelivery(organization=other, request=row)])
        models = (ExternalAgentRequest, ExternalAgentReceipt, ExternalAgentDelivery, ExternalAgentDeliveryItem, ExternalAgentTombstone)
        for tenant_id in (None, other.pk, self.organization.pk):
            with transaction.atomic():
                if tenant_id:
                    with tenant_atomic(tenant_id), connection.cursor() as cursor:
                        cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
                        self.assertEqual([model.objects.count() for model in models], [1 if tenant_id == self.organization.pk else 0] * 5)
                else:
                    with connection.cursor() as cursor:
                        cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
                        self.assertEqual([model.objects.count() for model in models], [0] * 5)

    def test_takeover_waits_for_started_handoff_and_blocks_next_one(self):
        from chatballs.ai.external_agents import delivery
        from chatballs.ai.provider.base import ProviderRejected

        row = self.request()
        self.claim()
        self.accept(row, self.result(row))
        with tenant_atomic(self.context):
            item_id = delivery.claim(self.context, self.conversation.pk)[0]
        entered, release, changing, changed = Event(), Event(), Event(), Event()

        def send():
            close_old_connections()
            try:
                with delivery_handoff(item_id, self.context, self.conversation.pk):
                    entered.set()
                    if not release.wait(10):
                        raise TimeoutError("test handoff not released")
            finally:
                close_old_connections()

        def takeover():
            close_old_connections()
            try:
                with tenant_atomic(self.context):
                    changing.set()
                    Conversation.objects.filter(pk=self.conversation.pk).update(control_mode="HUMAN")
                changed.set()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            sending = pool.submit(send)
            self.assertTrue(entered.wait(10))
            change = pool.submit(takeover)
            try:
                self.assertTrue(changing.wait(10))
                self.assertFalse(changed.wait(.1))
            finally:
                release.set()
            sending.result(timeout=10)
            change.result(timeout=10)
        self.assertTrue(changed.is_set())
        with self.assertRaises(ProviderRejected), delivery_handoff(item_id, self.context, self.conversation.pk):
            self.fail("revoked handoff must not enter")
