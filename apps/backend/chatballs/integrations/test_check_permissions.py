"""Проверка интеграции сохраняет RLS-права при собственной транзакции view."""

from django.db import connection
from django.test import TransactionTestCase

from chatballs.identity.models import HumanUser, Organization, OrganizationMembership
from chatballs.integrations.models import Integration
from chatballs.testing import TenantAPIClient


class IntegrationCheckRuntimePermissionsTests(TransactionTestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Checks", slug="check-permissions")
        self.admin = HumanUser.objects.create_user(email="check-admin@example.test")
        self.employee = HumanUser.objects.create_user(email="check-employee@example.test")
        for user, role in ((self.admin, "ADMIN"), (self.employee, "EMPLOYEE")):
            OrganizationMembership.objects.create(
                organization=self.organization, user=user, role=role, position_title=role,
            )
        self.integration = Integration.objects.create(
            organization=self.organization, kind="LLM_PROVIDER", provider="DEMO", name="Checks",
        )
        other = Organization.objects.create(name="Other", slug="check-permissions-other")
        self.foreign = Integration.objects.create(
            organization=other, kind="LLM_PROVIDER", provider="DEMO", name="Other",
        )

    def check_as_runtime(self, user, integration):
        client = TenantAPIClient()
        client.force_authenticate(user)
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE chatballs_runtime_app")
        try:
            return client.post(
                f"/api/v1/organizations/{self.organization.public_id}/integrations/{integration.id}/test/",
            )
        finally:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE")

    def test_admin_can_check_under_runtime_rls_without_expanding_other_access(self):
        # Штатный DEMO выполняет настоящую локальную проверку без внешнего API.
        own = self.check_as_runtime(self.admin, self.integration)
        self.assertEqual(own.status_code, 200, own.content)
        self.assertEqual(own.json()["integration"]["status"], "OK")
        forbidden = self.check_as_runtime(self.employee, self.integration)
        self.assertEqual(forbidden.status_code, 403, forbidden.content)
        foreign = self.check_as_runtime(self.admin, self.foreign)
        self.assertEqual(foreign.status_code, 404, foreign.content)
