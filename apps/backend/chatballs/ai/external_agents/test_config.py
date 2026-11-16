import json

from django.db import connection

from chatballs.ai.external_agents.config_models import (
    ExternalAgentBinding,
    ExternalAgentConnection,
)
from chatballs.ai.external_agents.testing import ConfigurationCase
from chatballs.identity.audit_models import AuditEvent
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.models import ServiceConnectionSettings


class ConfigurationTests(ConfigurationCase):
    def test_default_off_and_enable_without_configuration(self):
        self.assertFalse(self.organization.external_execution_enabled)
        self.assertEqual(self.agent.execution_mode, "builtin")
        self.enable()
        self.assertEqual(self.client.get(self.url).json()["connections"], [])
        self.transport.assert_not_called()

    def test_settings_are_owner_admin_only(self):
        for role, expected in [("EMPLOYEE", 403), ("ADMIN", 200), ("OWNER", 200)]:
            self.membership.role = role
            self.membership.save(update_fields=["role"])
            response = self.client.patch(self.url, {"enabled": True}, format="json")
            self.assertEqual(response.status_code, expected, response.content)

    def test_disabled_cannot_be_bypassed_in_agent_api(self):
        response = self.client.patch(
            f"/api/v1/organizations/{self.organization.public_id}/agents/{self.channel.pk}/",
            {"executionMode": "external"}, format="json")
        self.assertEqual(response.status_code, 400, response.content)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.execution_mode, "builtin")
        self.transport.assert_not_called()

    def test_new_key_only_once_encrypted_outgoing_and_hidden_catalog(self):
        result = self.connect()
        row = ExternalAgentConnection.objects.get(pk=result["connection"]["id"])
        self.assertNotEqual(result["incomingKey"], "outbound-test-secret")
        self.assertNotIn(result["incomingKey"], row.inbound_key_hash)
        self.assertNotIn("outbound-test-secret", json.dumps(self.client.get(self.url).json()))
        self.assertNotIn("incomingKey", json.dumps(self.client.get(self.url).json()))
        self.assertNotIn(result["incomingKey"], json.dumps(list(AuditEvent.objects.values()), default=str))
        self.assertEqual(ServiceConnectionSettings.objects.get(integration=row.integration).adapter_key, "external_agent_v1")
        with connection.cursor() as cursor:
            cursor.execute("SELECT credentials FROM integrations_serviceconnectionsettings WHERE integration_id = %s", [row.integration_id])
            self.assertNotIn("outbound-test-secret", cursor.fetchone()[0])
        adapter = default_registry().adapter("external_agent_v1")
        self.assertFalse(adapter.listed)
        self.assertEqual(adapter.operations, ())
        crm = f"/api/v1/organizations/{self.organization.public_id}/integrations/services/"
        self.assertEqual(self.client.get(crm).json()["items"], [])
        self.assertEqual(self.client.get(crm + f"{row.integration_id}/").status_code, 404)
        request = self.transport.call_args.args[0]
        self.assertEqual((request.method, request.url), ("GET", "https://executor.example.invalid/v1/capabilities"))
        self.assertEqual(request.headers["Authorization"], "Bearer outbound-test-secret")

    def test_disable_preserves_configuration_and_execution_mode(self):
        result = self.connect()
        identifier = result["connection"]["id"]
        self.bind(identifier)
        from chatballs.ai.external_agents.config_bindings import select_execution
        select_execution(self.context, self.agent.pk, "external")
        self.client.patch(self.url, {"enabled": False}, format="json")
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.execution_mode, "external")
        self.assertEqual(ExternalAgentConnection.objects.count(), 1)
        self.assertTrue(ExternalAgentBinding.objects.get().policy_accepted)
        self.assertEqual(self.client.get(self.url).json()["connections"][0]["id"], identifier)

    def test_invalid_binding_and_default_empty_policy(self):
        identifier = self.connect()["connection"]["id"]
        self.bind(identifier)
        binding = ExternalAgentBinding.objects.get()
        self.assertEqual((binding.standard_fields, binding.custom_fields, binding.template_ids), ([], [], []))
        url = self.url + f"connections/{identifier}/bindings/{self.agent.pk}/"
        for body in [{"standardFields": ["secret"]}, {"ordinaryTimeout": True},
                     {"customFields": [{"sourceConnectionId": 999999, "fieldId": "city"}]},
                     {"templateIds": ["unknown"]}, {"organizationId": self.organization.pk}]:
            self.assertEqual(self.client.put(url, body, format="json").status_code, 400)

    def test_off_prevents_setup_without_transport(self):
        response = self.client.post(self.url + "connections/", {
            "name": "Executor", "baseUrl": "https://executor.example.invalid", "outboundKey": "test-key",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.transport.assert_not_called()

    def test_failed_compatibility_check_revokes_previous_readiness(self):
        from chatballs.integrations.adapters.transport import TransportResponse

        identifier = self.connect()["connection"]["id"]
        self.transport.return_value = TransportResponse(200, "application/json", "", body=b'{"versions":["2"]}')
        response = self.client.post(self.url + f"connections/{identifier}/check/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.client.get(self.url).json()["connections"][0]["compatible"])

    def test_foreign_connection_and_agent_ids_are_hidden(self):
        from chatballs.ai.models import AIAgent
        from chatballs.channels.models import Channel
        from chatballs.identity.models import Organization

        other = Organization.objects.create(name="Other", slug="external-other")
        channel = Channel.objects.create(organization=other, name="Other", code="other")
        agent = AIAgent.objects.create(channel=channel, name="Other")
        identifier = self.connect()["connection"]["id"]
        url = self.url + f"connections/{identifier}/bindings/{agent.pk}/"
        self.assertEqual(self.client.put(url, {"externalAgentId": "other"}, format="json").status_code, 404)
        url = self.url + f"connections/{identifier + 10000}/"
        self.assertEqual(self.client.patch(url, {"enabled": True}, format="json").status_code, 404)

    def test_integral_decimal_capabilities_are_persisted_exactly(self):
        response = self.transport.return_value
        self.transport.return_value = type(response)(response.status, response.content_type, response.url,
            body=response.body.replace(b"2592000", b"2592000.0").replace(b"262144", b"262144.0"))
        identifier = self.connect()["connection"]["id"]
        row = ExternalAgentConnection.objects.get(pk=identifier)
        self.assertEqual(row.capabilities["dedupRetentionSeconds"], 2592000)
