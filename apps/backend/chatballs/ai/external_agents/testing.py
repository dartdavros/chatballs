"""Isolated test database objects; transport responses never leave the test process."""

import json
from unittest.mock import patch

from django.test import TestCase

from chatballs.ai.models import AIAgent
from chatballs.channels.models import Channel
from chatballs.identity.models import HumanUser, Organization, OrganizationMembership
from chatballs.integrations.adapters.transport import (
    GuardedTransport,
    TransportResponse,
)
from chatballs.testing import TenantAPIClient, tenant_context_for

CONTENT = ["text", "file", "image", "contact", "contact_request", "formatted"]
CAPABILITIES = {"versions": ["1"], "contentTypes": CONTENT,
                "directions": {"fromChatballs": CONTENT, "toChatballs": [item for item in CONTENT if item != "contact"]},
                "durableIdempotency": True, "statusLookup": True, "callbacks": True, "cancel": True,
                "dedupRetentionSeconds": 2592000, "maxJsonBytes": 262144}


class ConfigurationData:
    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(name="External test", slug="external-test")
        self.user = HumanUser.objects.create_user(email="external-test@example.invalid")
        self.membership = OrganizationMembership.objects.create(
            organization=self.organization, user=self.user, role="OWNER")
        self.context = tenant_context_for(self.user, self.organization)
        self.channel = Channel.objects.create(organization=self.organization, name="Agent", code="external-test")
        self.agent = AIAgent.objects.create(channel=self.channel, name="Agent", status="ACTIVE")
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.user)
        self.url = f"/api/v1/organizations/{self.organization.public_id}/settings/external-execution/"
        self.transport = patch.object(GuardedTransport, "send", return_value=TransportResponse(
            status=200, content_type="application/json", url="", body=json.dumps(CAPABILITIES).encode(),
        )).start()
        self.addCleanup(patch.stopall)

    def enable(self):
        response = self.client.patch(self.url, {"enabled": True}, format="json")
        self.assertEqual(response.status_code, 200, response.content)

    def connect(self):
        self.enable()
        response = self.client.post(self.url + "connections/", {
            "name": "Executor", "baseUrl": "https://executor.example.invalid/v1", "outboundKey": "outbound-test-secret",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        identifier = response.json()["connection"]["id"]
        checked = self.client.post(self.url + f"connections/{identifier}/check/", {}, format="json")
        self.assertEqual(checked.status_code, 200, checked.content)
        key = self.client.post(self.url + f"connections/{identifier}/key/", {}, format="json")
        self.assertEqual(key.status_code, 200, key.content)
        return key.json()

    def bind(self, connection_id, **policy):
        response = self.client.put(self.url + f"connections/{connection_id}/bindings/{self.agent.pk}/", {
            "externalAgentId": "service-agent", "policyAccepted": True, **policy,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()


class ConfigurationCase(ConfigurationData, TestCase):
    pass
