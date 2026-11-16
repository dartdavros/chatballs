"""Real PostgreSQL admission races, tenant boundaries and immutable ACK storage."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TransactionTestCase
from rest_framework.exceptions import PermissionDenied

from chatballs.ai.external_agents import handoff_request, proactive
from chatballs.ai.external_agents.auth import authenticated
from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.ingress import Conflict
from chatballs.ai.external_agents.operation_models import ExternalAgentOperation
from chatballs.ai.external_agents.operation_testing import OperationData
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.ai.external_agents.send_guards import delivery_handoff
from chatballs.conversations.ingest import ingest_inbound
from chatballs.conversations.models import ConnectionIdentity, Conversation, Message
from chatballs.conversations.transports.base import InboundMessage
from chatballs.identity.models import Organization
from chatballs.tenancy.database import tenant_atomic


class OperationConcurrencyTests(OperationData, RuntimeData, TransactionTestCase):
    def invoke(self, body, service=proactive):
        with authenticated("Bearer " + self.created["incomingKey"]) as (context, conn):
            return service.accept(context, conn, self.conversation.pk, body)

    @staticmethod
    def in_thread(action):
        close_old_connections()
        try:
            return action()
        finally:
            close_old_connections()

    def blocked_pair(self, first, second):
        """Hold the first operation's lock after its writes until the second waits."""
        entered, release, attempting, finished = Event(), Event(), Event(), Event()

        def holding():
            with tenant_atomic(self.context):
                value = first()
                entered.set()
                if not release.wait(20):
                    raise TimeoutError("operation not released")
            return value

        def waiting():
            attempting.set()
            try:
                return second()
            finally:
                finished.set()

        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(self.in_thread, holding)
            self.assertTrue(entered.wait(20))
            b = pool.submit(self.in_thread, waiting)
            try:
                self.assertTrue(attempting.wait(20))
                self.assertFalse(finished.wait(.1))
            finally:
                release.set()
            return a.result(timeout=30), b.result(timeout=30)

    def test_inbound_wins_lock_then_proactive_refuses_without_receipt(self):
        self.prepare_session()
        ConnectionIdentity.objects.create(contact=self.contact, connection=self.messaging, external_user_id="test-user")
        body = self.operation_body()

        def incoming():
            with patch("chatballs.conversations.transports.download_avatar", return_value=None):
                ingest_inbound(self.messaging, InboundMessage(external_id="race", user_id="test-user",
                    chat_id="test-chat", text="Client queue", display_name="Customer"))

        def initiative():
            try:
                self.invoke(body)
            except Conflict as error:
                return error.get_codes()
            return "unexpected_acceptance"

        _, outcome = self.blocked_pair(incoming, initiative)
        self.assertEqual(outcome, "conversation_busy")
        self.assertFalse(ExternalAgentOperation.objects.exists())
        self.assertEqual(Conversation.objects.count(), 1)

    def test_takeover_wins_lock_then_proactive_cannot_publish(self):
        self.prepare_session()
        body = self.operation_body()
        before = Message.objects.count()

        def takeover():
            Conversation.objects.filter(pk=self.conversation.pk).update(control_mode="HUMAN")

        def initiative():
            try:
                self.invoke(body)
            except PermissionDenied:
                return "denied"
            return "unexpected_acceptance"

        _, outcome = self.blocked_pair(takeover, initiative)
        self.assertEqual(outcome, "denied")
        self.assertEqual(Message.objects.count(), before)
        self.assertFalse(ExternalAgentOperation.objects.exists())

    def test_duplicate_proactive_commits_one_batch_and_one_ack(self):
        self.prepare_session()
        body = self.operation_body()
        first, replay = self.blocked_pair(lambda: self.invoke(body), lambda: self.invoke(body))
        self.assertEqual([first[1], replay[1]], [202, 200])
        self.assertEqual(first[0], replay[0])
        self.assertEqual(ExternalAgentOperation.objects.count(), 1)
        self.assertEqual(ExternalAgentDeliveryItem.objects.filter(delivery__public_id=body["deliveryId"]).count(), 1)

    def test_handoff_waits_for_started_send_then_revokes_remaining_items(self):
        from chatballs.ai.external_agents import delivery
        from chatballs.ai.provider.base import ProviderRejected

        self.prepare_session()
        self.invoke(self.operation_body())
        with tenant_atomic(self.context):
            item_id = delivery.claim(self.context, self.conversation.pk)[0]

        def sending():
            with delivery_handoff(item_id, self.context, self.conversation.pk):
                pass

        body = self.operation_body("handoff")
        _, ack = self.blocked_pair(sending, lambda: self.invoke(body, handoff_request))
        self.assertEqual(ack[0]["state"], "handed_off")
        self.assertEqual(ExternalAgentDeliveryItem.objects.get(pk=item_id).state, "unknown")
        with self.assertRaises(ProviderRejected), delivery_handoff(item_id, self.context, self.conversation.pk):
            self.fail("revoked delivery may not start")

    def test_operation_receipts_enforce_rls_tenant_fk_immutability_and_session_cleanup(self):
        self.prepare_session()
        self.invoke(self.operation_body("handoff"), handoff_request)
        row = ExternalAgentOperation.objects.get()
        other = Organization.objects.create(name="Other", slug="operation-other")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExternalAgentOperation.objects.filter(pk=row.pk).update(ack={})
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExternalAgentOperation.objects.bulk_create([ExternalAgentOperation(
                organization=other, session=self.session, operation="handoff", public_id=row.public_id,
                authorization_id=row.authorization_id, digest=row.digest)])
        for tenant in (None, other.pk, self.organization.pk):
            with transaction.atomic():
                if tenant:
                    with tenant_atomic(tenant), connection.cursor() as cursor:
                        cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
                        self.assertEqual(ExternalAgentOperation.objects.count(), int(tenant == self.organization.pk))
                else:
                    with connection.cursor() as cursor:
                        cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
                        self.assertEqual(ExternalAgentOperation.objects.count(), 0)
        ExternalAgentRequest.objects.filter(session=self.session).delete()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM ai_externalagentsession WHERE id = %s", [self.session.pk])
        self.assertFalse(ExternalAgentOperation.objects.exists())
