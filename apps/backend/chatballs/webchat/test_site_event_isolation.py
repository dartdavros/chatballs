from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import DatabaseError, connection, connections, transaction
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from chatballs.identity.models import Organization
from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat.proactive_models import SiteEventLaunch
from chatballs.webchat.site_event_test_base import SiteEventSetup


class SiteEventIsolationTests(SiteEventSetup, TransactionTestCase):
    def test_runtime_rls_and_database_relations_reject_another_tenant(self):
        session = self.issue()
        self.assertEqual(self.emit().status_code, 202)
        other = Organization.objects.create(name="Other", slug="site-isolation-other")
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE chatballs_runtime_app")
        try:
            with tenant_atomic(other.pk):
                self.assertEqual(SiteEventLaunch.objects.count(), 0)
                with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
                    cursor.execute("""INSERT INTO webchat_siteeventlaunch
                        (organization_id, session_id, rule_id, rule_digest, origin, mode_version,
                         control_version, agent_id_snapshot, agent_version, state, created_at)
                        VALUES (%s, %s, 'foreign-rule', '', '', 1, 0, 0, '', 'pending', NOW())""", [other.pk, session.pk])
            with tenant_atomic(self.tenant):
                self.assertEqual(SiteEventLaunch.objects.count(), 1)
        finally:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE")

    def test_parallel_new_event_ids_share_one_atomic_once_rule_marker(self):
        self.issue()
        barrier = Barrier(2)
        def emit(event_id):
            connections.close_all()
            try:
                client = APIClient()
                barrier.wait(timeout=15)
                response = client.post("/api/v1/webchat/site-events/", {
                    **self.event, "eventId": event_id, "hostOrigin": "https://site.example",
                }, format="json", HTTP_AUTHORIZATION=f"Bearer {self.token}")
                return response.status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(emit, ("tab-a", "tab-b")))
        self.assertEqual(sorted(results), [200, 202])
        self.assertEqual(SiteEventLaunch.objects.count(), 1)
        self.assertEqual(EventReceipt.objects.filter(event_key="webchat.site_event").count(), 1)
