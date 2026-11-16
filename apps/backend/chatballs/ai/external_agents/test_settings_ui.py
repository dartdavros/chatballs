"""Real local API boundaries in the isolated test database."""

from chatballs.ai.external_agents.config_models import ExternalAgentBinding, ExternalAgentConnection
from chatballs.ai.external_agents.testing import ConfigurationCase
from chatballs.integrations.models import Integration


class SettingsUiTests(ConfigurationCase):
    def test_save_does_not_check_or_issue_a_key(self):
        self.enable()
        response = self.client.post(self.url + "connections/", {
            "name": "Executor", "baseUrl": "https://executor.example.invalid/v1", "outboundKey": "secret",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.transport.assert_not_called()
        self.assertNotIn("incomingKey", response.json())
        self.assertFalse(response.json()["connection"]["compatible"])
        self.assertFalse(response.json()["connection"]["keyConfigured"])
        identifier = response.json()["connection"]["id"]
        response = self.client.put(self.url + f"connections/{identifier}/bindings/{self.agent.pk}/", {
            "externalAgentId": "test", "policyAccepted": True,
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ExternalAgentBinding.objects.exists())

    def test_catalog_keeps_sources_separate_and_excludes_foreign_data(self):
        from chatballs.identity.models import Organization

        for name in ("First", "Second"):
            Integration.objects.create(organization=self.organization, kind="MESSENGER", provider="WEB",
                name=name, config={"fields": [{"id": name, "key": "city", "label": "City", "type": "string"}]})
        other = Organization.objects.create(name="Other", slug="settings-ui-other")
        Integration.objects.create(organization=other, kind="MESSENGER", provider="WEB", name="Foreign",
            config={"fields": [{"id": "private", "label": "Secret", "type": "string"}]})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)
        fields = response.json()["catalog"]["customFields"]
        self.assertEqual([field["fieldId"] for field in fields], ["First", "Second"])
        self.assertNotEqual(fields[0]["sourceConnectionId"], fields[1]["sourceConnectionId"])
        self.assertNotIn("Secret", str(response.json()))
        self.transport.assert_not_called()

    def test_configuration_save_is_atomic_and_checks_revision(self):
        identifier = self.connect()["connection"]["id"]
        self.bind(identifier)
        saved = self.client.get(self.url).json()["connections"][0]
        url = self.url + f"connections/{identifier}/configuration/"
        body = {"revision": saved["revision"], "bindingRevisions": {str(item["agentId"]): [item["revision"], item["policyVersion"]]
                for item in saved["bindings"]}, "connection": {"name": "Changed"},
                "bindings": [{"agentId": self.agent.pk, "externalAgentId": "test", "standardFields": ["secret"]}],
                "removeAgentIds": []}
        self.assertEqual(self.client.put(url, body, format="json").status_code, 400)
        self.assertEqual(ExternalAgentConnection.objects.get(pk=identifier).integration.name, "Executor")
        body["bindings"] = []
        body["revision"] -= 1
        self.assertEqual(self.client.put(url, body, format="json").status_code, 400)
        body["revision"] = saved["revision"]
        response = self.client.put(url, body, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["connections"][0]["name"], "Changed")
