from django.db import DatabaseError, connection, transaction

from chatballs.ai.diagnostic_models import TurnDiagnostic
from chatballs.conversations.diagnostic_testing import DiagnosticTestCase
from chatballs.conversations.models import Message, MessageAuthor
from chatballs.identity.models import Organization
from chatballs.tenancy.database import tenant_atomic


class DiagnosticRlsTests(DiagnosticTestCase):
    def setUp(self):
        super().setUp()
        self.other = Organization.objects.create(name="Other", slug="diagnostic-rls-other")
        self.message = Message.objects.create(conversation=self.conversation,
                                              author_type=MessageAuthor.CONTACT)

    def as_runtime(self, organization, action):
        try:
            with tenant_atomic(organization.id):
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
                return action()
        finally:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE")

    def test_runtime_can_store_and_read_only_its_own_trace(self):
        trace = self.as_runtime(self.organization, lambda: TurnDiagnostic.objects.create(
            message=self.message, payload={"state": "running"},
        ))
        own = self.as_runtime(self.organization, lambda: list(TurnDiagnostic.objects.values_list("id", flat=True)))
        foreign = self.as_runtime(self.other, lambda: list(TurnDiagnostic.objects.values_list("id", flat=True)))
        self.assertEqual(own, [trace.id])
        self.assertEqual(foreign, [])

    def test_database_rejects_forged_tenant_keys_even_without_model_validation(self):
        for organization, tenant in ((self.organization, self.other), (self.other, self.other)):
            with self.assertRaises(DatabaseError), transaction.atomic():
                self.as_runtime(tenant, lambda organization=organization: TurnDiagnostic.objects.bulk_create([
                    TurnDiagnostic(organization=organization, message=self.message, payload={})
                ]))
