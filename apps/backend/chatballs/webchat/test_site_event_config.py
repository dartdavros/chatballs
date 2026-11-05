"""Meaningful site rule boundaries; no live provider or site is simulated."""

from uuid import uuid4

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from chatballs.channels.models import Channel
from chatballs.identity.models import Organization
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.integrations.web_config import normalized_web_config
from chatballs.webchat.site_event_config import configured_scenario, normalize_rule, public_rule
from chatballs.webchat.site_event_schema import normalize_schema, validate_data, validate_envelope
from chatballs.webchat.testing import create_web_widget


def rule(**changes):
    return {"name": "checkout.help", "invitation": "Help?", "scenario": str(uuid4()),
        "schema": [{"name": "category", "type": "string", "maxLength": 120, "required": True}], **changes}


class SiteSchemaTests(SimpleTestCase):
    def test_typed_bounded_values_and_no_unknown_fields(self):
        schema = normalize_schema([
            {"name": "category", "type": "string", "maxLength": 4, "required": True},
            {"name": "total", "type": "number", "minimum": 0, "maximum": 100},
            {"name": "available", "type": "boolean"},
        ])
        validate_data(schema, {"category": "food", "total": 12.5, "available": True})
        for data in ({}, {"category": "longer"}, {"category": "food", "unknown": "secret"},
                {"category": None}, {"category": "food", "total": True},
                {"category": "food", "total": 10 ** 400}, {"category": "food", "total": float("nan")},
                {"category": "food", "available": 1}):
            with self.subTest(data_type=type(data)), self.assertRaises(ValidationError) as error:
                validate_data(schema, data)
            self.assertNotIn("secret", str(error.exception))

    def test_schema_rejects_unbounded_nested_and_duplicate_fields(self):
        for schema in ([{"name": "x", "type": "string"}], [{"name": "x", "type": "object"}],
                [{"name": "x", "type": "number", "minimum": 10, "maximum": 1}],
                [{"name": "x", "type": "boolean"}] * 2,
                [{"name": "x", "type": "string", "maxLength": 4001}],
                [{"name": "x", "type": "boolean", "instructions": "secret"}]):
            with self.subTest(schema=schema), self.assertRaises(ValidationError):
                normalize_schema(schema)

    def test_envelope_size_is_utf8_bytes_and_no_authority_parameters(self):
        base = {"name": "checkout.help", "eventId": "same-event", "data": {}}
        validate_envelope(base)
        for payload in ({**base, "data": {"x": "я" * 11000}}, {**base, "scenario_id": 1},
                {**base, "eventId": ""}, {**base, "grants": []}, {**base, "data": {"x": float("inf")}}):
            with self.assertRaises(ValidationError):
                validate_envelope(payload)

    def test_rule_identity_is_server_owned_default_off_and_legacy_preserves_rule(self):
        saved = normalize_rule({"siteEvent": rule(id="browser-picked")}, {})
        self.assertFalse(saved["active"])
        self.assertNotEqual(saved["id"], "browser-picked")
        changed = normalize_rule({"siteEvent": rule(id="reset-attempt")}, {"siteEvent": saved})
        self.assertEqual(changed["id"], saved["id"])
        legacy = normalized_web_config({}, {"siteEvent": saved})
        self.assertEqual(legacy["siteEvent"], saved)
        self.assertIsNone(normalize_rule({"siteEvent": None}, legacy))


class SiteRuleIsolationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Site", slug="site-events-config")
        channel = Channel.objects.create(organization=self.organization, name="Site", code="site-events-config")
        self.integration = create_web_widget(channel).integration

    def scenario(self, organization):
        document = empty_definition()
        document["triggers"] = [{"id": "site", "kind": "chatballs", "event": "webchat.site_event"}]
        row = ScenarioDefinition(organization=organization, name="First contact")
        row.definition = document
        row.save()
        return row

    def test_only_own_scenario_and_safe_public_projection(self):
        own = self.scenario(self.organization)
        private = normalize_rule({"siteEvent": rule(scenario=str(own.public_id), active=True)}, {})
        self.integration.config = {"siteEvent": private}
        self.assertEqual(configured_scenario(self.integration), own)
        public = public_rule(self.integration)
        self.assertEqual(set(public), {"name", "schema", "invitation"})
        self.assertNotIn(str(own.public_id), str(public))
        other_org = Organization.objects.create(name="Other", slug="site-events-other")
        other = self.scenario(other_org)
        self.integration.config = {"siteEvent": {**private, "scenario": str(other.public_id)}}
        with self.assertRaises(ValidationError):
            configured_scenario(self.integration)
        self.integration.config = {"siteEvent": {**private, "active": False}}
        self.assertIsNone(public_rule(self.integration))

    def test_scenario_without_declared_event_cannot_be_selected(self):
        row = self.scenario(self.organization)
        row.definition = empty_definition()
        row.save()
        self.integration.config = {"siteEvent": rule(scenario=str(row.public_id))}
        with self.assertRaises(ValidationError):
            configured_scenario(self.integration)

    def test_catalog_summary_exposes_eligibility_without_a_full_definition(self):
        from chatballs.integrations.scenarios.payloads import scenario_payload
        row = self.scenario(self.organization)
        summary = scenario_payload(row, detail=False)
        self.assertEqual(summary["nativeEvents"], ["webchat.site_event"])
        self.assertEqual(summary["accessScope"], "conversation")
        self.assertNotIn("definition", summary)
