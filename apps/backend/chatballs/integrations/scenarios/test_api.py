"""Only the definition API; no external requests or effects in these tests."""

from django.db import IntegrityError, InternalError, ProgrammingError, connection, transaction
from django.test import TransactionTestCase

from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import EmployeeRole, HumanUser, Organization, OrganizationMembership
from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
    ServiceConnectionSettings,
)
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.tenancy.database import tenant_atomic
from chatballs.testing import TenantAPIClient


class ScenarioAPICase(TransactionTestCase):
    def setUp(self):
        self.owner = bootstrap_owner(email="scenario-owner@example.com", password="test-password").owner
        self.organization = Organization.objects.get(slug="demo")
        self.other = Organization.objects.create(name="Other", slug="scenario-other")
        self.other_owner = HumanUser.objects.create_user(email="scenario-other@example.com")
        OrganizationMembership.objects.create(organization=self.other, user=self.other_owner, role=EmployeeRole.OWNER)
        self.employee = HumanUser.objects.create_user(email="scenario-employee@example.com")
        OrganizationMembership.objects.create(organization=self.organization, user=self.employee, role=EmployeeRole.EMPLOYEE)
        self.admin = HumanUser.objects.create_user(email="scenario-admin@example.com")
        OrganizationMembership.objects.create(organization=self.organization, user=self.admin, role=EmployeeRole.ADMIN)
        self.client = self.client_for(self.owner)

    def client_for(self, user):
        client = TenantAPIClient()
        client.force_authenticate(user)
        return client

    def url(self, suffix="", organization=None):
        org = organization or self.organization
        return f"/api/v1/organizations/{org.public_id}/integrations/scenarios/{suffix}"

    def create(self):
        response = self.client.post(self.url(), {"name": "Example", "definition": empty_definition()}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["scenario"]

    def as_runtime(self, fn):
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE chatballs_runtime_app")
        try:
            return fn()
        finally:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE")


class ScenarioAPITests(ScenarioAPICase):
    def test_admin_can_edit_disabled_draft_but_enable_requires_valid_structure(self):
        scenario = self.create()
        self.assertFalse(scenario["enabled"])
        payload = {"name": "Changed", "revision": 1, "definition": scenario["definition"], "enabled": True}
        response = self.client_for(self.admin).put(self.url(f"{scenario['id']}/"), payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()["issues"])
        payload["enabled"] = False
        saved = self.client_for(self.admin).put(self.url(f"{scenario['id']}/"), payload, format="json")
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertEqual(saved.json()["scenario"]["revision"], 2)
        conflict = self.client.put(self.url(f"{scenario['id']}/"), payload, format="json")
        self.assertEqual(conflict.status_code, 409)
        delete_conflict = self.client.delete(self.url(f"{scenario['id']}/"), {"revision": 1}, format="json")
        self.assertEqual(delete_conflict.status_code, 409)

    def test_employee_has_no_editor_access(self):
        scenario = self.create()
        client = self.client_for(self.employee)
        self.assertEqual(client.get(self.url()).status_code, 403)
        self.assertEqual(client.get(self.url(f"{scenario['id']}/")).status_code, 403)
        self.assertEqual(client.post(self.url(), {"name": "No", "definition": empty_definition()}, format="json").status_code, 403)

    def test_runtime_rls_hides_foreign_definitions_and_rejects_owner_changes(self):
        scenario = self.as_runtime(self.create)
        other = self.client_for(self.other_owner)
        response = self.as_runtime(lambda: other.get(self.url(organization=self.other)))
        self.assertEqual(response.json()["items"], [])
        response = self.as_runtime(lambda: other.get(self.url(f"{scenario['id']}/", self.other)))
        self.assertEqual(response.status_code, 404)
        with self.assertRaises((IntegrityError, InternalError, ProgrammingError)):
            def move():
                with transaction.atomic(), tenant_atomic(self.organization.id):
                    ScenarioDefinition.objects.filter(public_id=scenario["id"]).update(organization_id=self.other.id)
            self.as_runtime(move)

    def test_copy_has_independent_revision_and_encrypted_content(self):
        scenario = self.create()
        response = self.client.post(self.url(f"{scenario['id']}/copy/"), {"name": "Copy"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        copied = response.json()["scenario"]
        self.assertNotEqual(copied["id"], scenario["id"])
        self.assertEqual(copied["revision"], 1)
        self.assertFalse(copied["enabled"])
        with connection.cursor() as cursor:
            cursor.execute("SELECT content FROM integrations_scenariodefinition WHERE public_id=%s", [copied["id"]])
            self.assertNotIn('"triggers"', cursor.fetchone()[0])

    def test_preset_copy_is_owned_and_adapter_definition_stays_unchanged(self):
        integration = Integration.objects.create(organization=self.organization, name="CRM", kind=IntegrationKind.SERVICE,
                                                  provider=IntegrationProvider.ADAPTER)
        ServiceConnectionSettings.objects.create(organization=self.organization, integration=integration,
            adapter_key="bitrix24", adapter_version=1, auth_method="webhook")
        url = f"/api/v1/organizations/{self.organization.public_id}/integrations/services/{integration.id}/presets/create_lead_from_conversation/"
        first = self.client.post(url, {}, format="json")
        self.assertEqual(first.status_code, 201, first.content)
        one = first.json()["scenario"]
        self.assertEqual(one["issues"], [])
        self.assertNotIn("ASSIGNED_BY_ID", one["definition"]["steps"][0]["inputs"]["fields"])
        self.assertNotIn("STATUS_ID", one["definition"]["steps"][0]["inputs"]["fields"])
        payload = {"name": "My copy", "definition": one["definition"], "revision": 1}
        self.assertEqual(self.client.put(self.url(f"{one['id']}/"), payload, format="json").status_code, 200)
        second = self.client.post(url, {}, format="json")
        self.assertEqual(second.status_code, 201, second.content)
        self.assertNotEqual(second.json()["scenario"]["id"], one["id"])
        unchanged = self.client.get(self.url(f"{one['id']}/")).json()["scenario"]
        self.assertEqual(unchanged["name"], "My copy")
        self.assertEqual(unchanged["revision"], 2)

    def test_client_cannot_assign_tenant_or_server_identity(self):
        for field in ("organization", "organizationId", "principal", "credentials"):
            response = self.client.post(self.url(), {"name": "No", "definition": empty_definition(), field: "arbitrary"}, format="json")
            self.assertEqual(response.status_code, 400, field)
