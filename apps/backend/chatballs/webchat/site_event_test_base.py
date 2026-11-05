"""Isolated Django test database setup, never data for the running application."""

from django.test import TestCase
from rest_framework.test import APIClient

from chatballs.ai.models import AIAgent
from chatballs.channels.models import Channel
from chatballs.identity.models import HumanUser, Organization, OrganizationMembership
from chatballs.integrations.automation_events.configuration import synchronize
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.tenancy.context import TenantContext
from chatballs.webchat.models import WebSession
from chatballs.webchat.site_event_config import normalize_rule
from chatballs.webchat.testing import create_web_widget


class SiteEventSetup:
    def setUp(self):
        self.organization = Organization.objects.create(name="Site events", slug="site-runtime")
        owner = HumanUser.objects.create_user(email="site-owner@example.test")
        member = OrganizationMembership.objects.create(organization=self.organization, user=owner, role="OWNER")
        self.tenant = TenantContext.for_membership(member)
        self.channel = Channel.objects.create(organization=self.organization, name="Site", code="site-runtime")
        provider = Integration.objects.create(organization=self.organization, name="Test contract",
            kind="LLM_PROVIDER", provider="CUSTOM", secret="test-not-used-on-network", status="OK",
            config={"base_url": "https://example.invalid/v1", "default_model": "test"})
        self.agent = AIAgent.objects.create(channel=self.channel, provider_integration=provider, status="ACTIVE", model="test")
        self.widget = create_web_widget(self.channel, allowed_origins=["https://site.example"])
        self.scenario = self.make_scenario("Selected")
        self.rule = normalize_rule({"siteEvent": {"name": "checkout.help", "invitation": "Help?",
            "scenario": str(self.scenario.public_id), "active": True,
            "schema": [{"name": "category", "type": "string", "maxLength": 120, "required": True}]}}, {})
        self.widget.integration.config = {"siteEvent": self.rule}
        self.widget.integration.save(update_fields=["config"])
        self.client = APIClient()
        self.event = {"name": "checkout.help", "eventId": "stable-1", "data": {"category": "private-category"}}

    def make_scenario(self, name):
        document = empty_definition()
        document["triggers"] = [{"id": "site", "kind": "chatballs", "event": "webchat.site_event"}]
        document["access"].update(delegated=True, scope="conversation")
        document["steps"] = [{"id": "first", "kind": "action", "connection": "chatballs",
            "target": "chatballs:webchat.first_reply", "inputs": {
                "instruction": {"source": "constant", "value": "Offer help with the selection."}}}]
        row = ScenarioDefinition(organization=self.organization, name=name, enabled=True)
        row.definition = document
        row.save()
        synchronize(self.tenant, row, {})
        return row

    def issue(self, consent=True):
        response = self.client.post("/api/v1/webchat/session/", {"widgetKey": self.widget.public_key,
            "hostOrigin": "https://site.example", **({"consentVersion": "v1"} if consent else {})}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.token = response.json()["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        return WebSession.objects.latest("pk")

    def emit(self, payload=None, origin="https://site.example"):
        return self.client.post("/api/v1/webchat/site-events/", {**(payload or self.event), "hostOrigin": origin}, format="json")


class SiteEventCase(SiteEventSetup, TestCase):
    pass
