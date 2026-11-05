"""Configuration boundaries against PostgreSQL, including runtime RLS."""

from django.db import connection

from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
    ServiceConnectionSettings,
)
from chatballs.integrations.scenario_state.subscriptions import ScenarioExternalKey
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.integrations.scenarios.external_keys import token_hash
from chatballs.integrations.scenarios.test_api import ScenarioAPICase


class ScenarioConfigurationTests(ScenarioAPICase):
    def test_valid_enable_then_disable_and_delete_without_effects(self):
        document = empty_definition()
        document["steps"] = [{"id": "pause", "kind": "wait", "mode": "duration", "duration": 60}]
        response = self.client.post(self.url(), {"name": "Wait", "definition": document, "enabled": True}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        row = response.json()["scenario"]
        self.assertEqual(row["issues"], [])
        self.assertTrue(row["enabled"])
        response = self.client.put(self.url(f"{row['id']}/"), {"name": row["name"], "definition": document, "revision": 1, "enabled": False}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.json()["scenario"]["enabled"])
        self.assertEqual(self.client.delete(self.url(f"{row['id']}/"), {"revision": 2}, format="json").status_code, 204)

    def test_api_key_is_one_time_hashed_rotatable_and_independent_on_copy(self):
        document = empty_definition()
        document["triggers"] = [{"id": "external", "kind": "api"}]
        document["access"]["delegated"] = True
        response = self.as_runtime(lambda: self.client.post(self.url(), {"name": "API", "definition": document}, format="json"))
        self.assertEqual(response.status_code, 201, response.content)
        scenario = response.json()["scenario"]
        original = scenario["externalKeys"][0]
        self.assertTrue(original["key"].startswith("cbk_"))
        self.assertIn(original["id"], original["url"])
        detail = self.client.get(self.url(f"{scenario['id']}/")).json()["scenario"]
        self.assertNotIn("key", detail["externalKeys"][0])
        self.assertEqual(ScenarioExternalKey.objects.get(public_id=original["id"]).token_hash, token_hash(original["key"]))
        rotate_url = self.url(f"{scenario['id']}/keys/external/rotate/")
        self.assertEqual(self.client.post(rotate_url, {"revision": 0}, format="json").status_code, 409)
        rotated = self.client.post(rotate_url, {"revision": 1}, format="json").json()["externalKey"]
        self.assertNotEqual(rotated["key"], original["key"])
        self.assertEqual(ScenarioExternalKey.objects.get(public_id=original["id"]).token_hash, token_hash(rotated["key"]))
        copied = self.client.post(self.url(f"{scenario['id']}/copy/"), {"name": "Copy"}, format="json").json()["scenario"]
        self.assertNotEqual(copied["externalKeys"][0]["key"], rotated["key"])
        other_url = self.url(f"{scenario['id']}/keys/external/rotate/", self.other)
        self.assertEqual(self.as_runtime(lambda: self.client_for(self.other_owner).post(other_url, {"revision": 1}, format="json")).status_code, 404)
        self.client.put(self.url(f"{scenario['id']}/"), {"name": "API", "revision": 1, "definition": empty_definition()}, format="json")
        self.assertFalse(ScenarioExternalKey.objects.filter(public_id=original["id"]).exists())

    def test_exchange_is_encrypted_revisioned_and_tenant_scoped(self):
        integration = Integration.objects.create(organization=self.organization, name="CRM", kind=IntegrationKind.SERVICE, provider=IntegrationProvider.ADAPTER)
        ServiceConnectionSettings.objects.create(organization=self.organization, integration=integration, adapter_key="bitrix24", adapter_version=1, auth_method="webhook")
        path = f"integrations/services/{integration.id}/synchronization/"
        url = f"/api/v1/organizations/{self.organization.public_id}/{path}"
        self.assertEqual(self.client.get(url).json()["revision"], 0)
        pair = {"id": "contact", "enabled": True, "left": {"connection": "chatballs", "entity": "contact"},
            "right": {"connection": str(integration.id), "entity": "contact"}, "direction": "both",
            "fields": [{"left": "name", "right": "NAME", "direction": "forward"}, {"left": "name", "right": "NAME", "direction": "reverse"}],
            "sourceOfTruth": "latest", "conflict": "manual", "deletion": "unlink", "causality": {"suppressEcho": True, "requireExplicitLink": True}}
        payload = {"revision": 0, "definition": {"version": 1, "synchronization": [pair]}}
        # Bitrix does not expose a conditional remote write. Preserve that
        # rejection and exercise the supported remote-to-native direction.
        self.assertEqual(self.client.put(url, payload, format="json").status_code, 400)
        pair["direction"] = "reverse"
        result = self.as_runtime(lambda: self.client.put(url, payload, format="json"))
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(result.json()["revision"], 1)
        self.assertEqual(self.client.put(url, payload, format="json").status_code, 409)
        with connection.cursor() as cursor:
            cursor.execute("SELECT content FROM integrations_servicesynchronizationsettings WHERE integration_id=%s", [integration.id])
            self.assertNotIn('"synchronization"', cursor.fetchone()[0])
        other_url = f"/api/v1/organizations/{self.other.public_id}/{path}"
        self.assertEqual(self.as_runtime(lambda: self.client_for(self.other_owner).get(other_url)).status_code, 404)
        self.assertEqual(self.client_for(self.employee).get(url).status_code, 403)
        payload["revision"] = 1
        pair["fields"][1]["left"] = "id"
        self.assertEqual(self.client.put(url, payload, format="json").status_code, 400)
