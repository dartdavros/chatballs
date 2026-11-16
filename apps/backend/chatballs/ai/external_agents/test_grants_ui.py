"""Re-acknowledgement of exact definitions, not names or a restored field key."""

from copy import deepcopy

from chatballs.ai.external_agents.config_bindings import select_execution
from chatballs.ai.external_agents.config_models import ExternalAgentBinding
from chatballs.ai.external_agents.grant_definitions import stale_grants
from chatballs.ai.external_agents.readiness import ready
from chatballs.ai.external_agents.testing import ConfigurationCase
from chatballs.integrations.models import Integration
from chatballs.webchat.field_schema import normalize_fields


class DefinitionGrantTests(ConfigurationCase):
    def test_changed_deleted_and_recreated_fields_do_not_inherit_permission(self):
        identifier = self.connect()["connection"]["id"]
        source = Integration.objects.create(organization=self.organization, name="Source", kind="MESSENGER", provider="WEB",
            config={"fields": normalize_fields([{"key": "city", "label": "City", "type": "string"}], [])})
        original = deepcopy(source.config)
        ref = {"sourceConnectionId": source.pk, "fieldId": original["fields"][0]["id"]}
        self.bind(identifier, customFields=[ref])
        select_execution(self.context, self.agent.pk, "external")
        self.agent.refresh_from_db()
        self.organization.refresh_from_db()
        self.assertTrue(ready(self.agent, self.organization))
        source.config["fields"][0]["type"] = "number"
        source.save(update_fields=["config"])
        binding = ExternalAgentBinding.objects.get()
        self.assertEqual(stale_grants(binding)["customFields"], [ref])
        self.assertFalse(ready(self.agent, self.organization))
        source.config = original
        source.save(update_fields=["config"])
        self.assertEqual(stale_grants(binding)["customFields"], [ref])
        self.bind(identifier, customFields=[ref])
        self.agent.refresh_from_db()
        self.assertTrue(ready(self.agent, self.organization))
        source.config = {"fields": normalize_fields([{"key": "city", "label": "City", "type": "string"}], [])}
        source.save(update_fields=["config"])
        self.assertNotEqual(source.config["fields"][0]["id"], ref["fieldId"])
        self.assertEqual(stale_grants(ExternalAgentBinding.objects.get())["customFields"], [ref])

    def test_reenable_preserves_settings_and_requires_check_and_explicit_permission(self):
        identifier = self.connect()["connection"]["id"]
        self.bind(identifier, standardFields=["name"], proactiveEnabled=True)
        select_execution(self.context, self.agent.pk, "external")
        self.client.patch(self.url, {"enabled": False}, format="json")
        self.enable()
        saved = self.client.get(self.url).json()["connections"][0]
        self.assertFalse(saved["compatible"])
        self.assertEqual(saved["bindings"][0]["standardFields"], ["name"])
        self.assertTrue(saved["bindings"][0]["proactiveEnabled"])
        self.assertFalse(saved["bindings"][0]["policyAccepted"])
        self.client.post(self.url + f"connections/{identifier}/check/", {}, format="json")
        self.agent.refresh_from_db()
        self.organization.refresh_from_db()
        self.assertFalse(ready(self.agent, self.organization))
        self.bind(identifier)
        self.agent.refresh_from_db()
        self.assertTrue(ready(self.agent, self.organization))
