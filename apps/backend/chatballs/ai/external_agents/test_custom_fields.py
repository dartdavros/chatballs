"""Typed complete snapshots, exact numbers and explicit export isolation."""

from decimal import Decimal

from django.db import connection, transaction
from django.test import TestCase

from chatballs.ai.external_agents.context_testing import ContextData
from chatballs.ai.external_agents.custom_fields import snapshot
from chatballs.ai.external_agents.json_payloads import dumps, loads
from chatballs.conversations.models import Contact, ContactFieldValue
from chatballs.identity.models import Organization
from chatballs.tenancy.database import tenant_atomic

EXAMPLES = {"string": "", "number": 0, "boolean": False, "datetime": "2026-11-16T12:34:56",
            "enum": "ready", "email": "test@example.invalid", "phone": "+79991234567",
            "url": "https://example.invalid/path"}


class CustomFieldTests(ContextData, TestCase):
    def test_standard_export_is_a_separate_explicit_allowlist(self):
        self.assertEqual(self.binding().standard_fields, [])
        self.contact.email, self.contact.phone = "private@example.invalid", "+79991234567"
        self.contact.description = "PRIVATE-INTERNAL"
        self.contact.save()
        self.bind(self.connection.pk, standardFields=["phone"])
        row = self.request()
        self.assertIsNotNone(self.claim())
        data = self.frozen(row)["context"]
        self.assertEqual(data["customer"]["fields"], {"phone": "+79991234567"})
        self.assertEqual(data["dataPolicy"]["fields"], ["phone"])
        self.assertEqual(data["customer"]["customFields"]["scope"], [])
        self.assertNotIn("PRIVATE-INTERNAL", dumps(data))
        self.assertNotIn("private@example.invalid", dumps(data))

    def test_all_eight_types_and_real_timestamps_roundtrip_the_request_contract(self):
        definitions = [{"key": f"custom_{kind}", "label": kind, "type": kind,
                        **({"options": [{"value": "ready", "label": "Ready", "color": "#123abc"}]}
                           if kind == "enum" else {})} for kind in EXAMPLES]
        source = self.source(definitions)
        rows = {kind: self.value(source, f"custom_{kind}", value) for kind, value in EXAMPLES.items()}
        self.grant(source)
        row = self.request()
        work = self.claim()
        self.assertIsNotNone(work)
        data = self.frozen(row)["context"]
        fields = data["customer"]["customFields"]
        self.assertEqual(data["customer"]["fields"], {})
        self.assertEqual(data["dataPolicy"]["customFields"], fields["scope"])
        self.assertEqual([item["key"] for item in fields["items"]], [f"custom_{kind}" for kind in EXAMPLES])
        for item in fields["items"]:
            self.assertEqual(item["status"], "set")
            self.assertEqual(item["value"], EXAMPLES[item["type"]])
            self.assertEqual(item["updatedAt"], rows[item["type"]].updated_at.isoformat().replace("+00:00", "Z"))
        self.assertEqual(fields["items"][4]["options"][0]["value"], "ready")
        self.assertNotIn("clearedAt", dumps(fields))

    def test_every_type_includes_unset_and_rejects_bad_values_without_original_data(self):
        definitions = [{"key": f"custom_{kind}", "label": kind, "type": kind} for kind in EXAMPLES]
        source = self.source(definitions)
        self.grant(source)
        self.assertEqual([item["status"] for item in snapshot(self.binding(), self.contact)["items"]], ["unset"] * 8)
        for kind in EXAMPLES:
            self.value(source, f"custom_{kind}", ["PRIVATE"] if kind == "string" else "PRIVATE")
        data = snapshot(self.binding(), self.contact)
        self.assertEqual([item["status"] for item in data["items"]], ["invalid"] * 8)
        self.assertTrue(all(item["value"] is None and item["updatedAt"] for item in data["items"]))
        self.assertNotIn("PRIVATE", dumps(data))

    def test_unset_clear_and_invalid_values_never_export_bad_input(self):
        source = self.source([{"key": "state", "label": "State", "type": "enum",
                               "options": [{"value": "ok", "label": "Okay"}]}])
        self.grant(source)
        binding = self.binding()
        self.assertEqual(snapshot(binding, self.contact)["items"][0]["status"], "unset")
        row = self.value(source, "state", "ok")
        row.delete()
        item = snapshot(binding, self.contact)["items"][0]
        self.assertEqual((item["status"], item["value"], item["updatedAt"]), ("unset", None, None))
        for bad, reason in (("PRIVATE-invalid", "option"), (True, "type"), ("PRIVATE" * 100, "length")):
            with self.subTest(reason=reason):
                ContactFieldValue.objects.filter(contact=self.contact).delete()
                value = self.value(source, "state", bad)
                item = snapshot(binding, self.contact)["items"][0]
                self.assertEqual((item["status"], item["value"], item["reasonCode"]), ("invalid", None, reason))
                self.assertEqual(item["updatedAt"], value.updated_at.isoformat().replace("+00:00", "Z"))
                self.assertNotIn("PRIVATE", dumps(item))

    def test_format_invalid_and_type_changes_use_current_schema(self):
        for kind in ("datetime", "email", "phone", "url", "number", "boolean"):
            with self.subTest(kind=kind):
                source = self.source([{"key": "value", "label": "Value", "type": kind}], name=kind)
                self.value(source, "value", "BAD-PRIVATE")
                self.grant(source)
                item = snapshot(self.binding(), self.contact)["items"][0]
                self.assertEqual(item["status"], "invalid")
                self.assertEqual(item["reasonCode"], "type" if kind in {"number", "boolean"} else "format")
                self.assertNotIn("BAD-PRIVATE", dumps(item))

    def test_same_key_sources_contact_and_tenant_are_independent(self):
        definition = [{"key": "same", "label": "Same", "type": "string", "aiAccess": "open"}]
        first, second = self.source(definition), self.source(definition, name="Second")
        self.value(first, "same", "first")
        self.value(second, "same", "second")
        other = Contact.objects.create(organization=self.organization, name="Other")
        self.value(first, "same", "OTHER-CONTACT", contact=other)
        tenant = Organization.objects.create(name="Foreign", slug="foreign-context")
        foreign = self.source(definition, organization=tenant)
        self.grant(second, first)
        data = snapshot(self.binding(), self.contact)
        self.assertEqual([item["value"] for item in data["items"]], ["first", "second"])
        self.assertEqual(len(data["scope"]), 2)
        invalid = self.client.put(self.url + f"connections/{self.connection.pk}/bindings/{self.agent.pk}/",
            {"externalAgentId": "service-agent", "customFields": [
                {"sourceConnectionId": foreign.pk, "fieldId": foreign.config["fields"][0]["id"]}]}, format="json")
        self.assertEqual(invalid.status_code, 400)
        self.grant()
        self.assertEqual(snapshot(self.binding(), self.contact)["items"], [])
        self.assertEqual(self.binding().standard_fields, [])

    def test_postgres_numbers_keep_precision_and_json_types_through_encryption_digest(self):
        source = self.source([{"key": "amount", "label": "Amount", "type": "number"}])
        value = self.value(source, "amount", 0)
        exact = "12345678901234567890.12345678901234567890123456789"
        with connection.cursor() as cursor:
            cursor.execute("UPDATE contact_field_values SET value = %s::jsonb WHERE id = %s", [exact, value.pk])
        self.grant(source)
        row = self.request()
        work = self.claim()
        self.assertIsNotNone(work)
        parsed = loads(work.request.body)
        number = parsed["context"]["customer"]["customFields"]["items"][0]["value"]
        self.assertEqual(number, Decimal(exact))
        self.assertEqual(self.frozen(row)["context"]["customer"]["customFields"]["items"][0]["value"], number)
        self.assertIn(exact, work.request.body.decode())

    def test_only_explicit_field_pair_exports_and_wrong_source_field_pair_is_rejected(self):
        source = self.source([
            {"key": "allowed", "label": "Allowed", "type": "string", "aiAccess": "open"},
            {"key": "private", "label": "Private", "type": "string", "aiAccess": "open"},
        ])
        second = self.source([{"key": "allowed", "label": "Allowed", "type": "string"}], name="Second")
        self.value(source, "allowed", "permitted")
        self.value(source, "private", "PRIVATE-FIELD")
        self.value(second, "allowed", "PRIVATE-SOURCE")
        ref = {"sourceConnectionId": source.pk, "fieldId": source.config["fields"][0]["id"]}
        self.bind(self.connection.pk, customFields=[ref])
        data = snapshot(self.binding(), self.contact)
        self.assertEqual(data["scope"], [{**ref, "sourceConnectionId": str(source.pk)}])
        self.assertEqual([item["value"] for item in data["items"]], ["permitted"])
        self.assertNotIn("PRIVATE", dumps(data))
        response = self.client.put(self.url + f"connections/{self.connection.pk}/bindings/{self.agent.pk}/",
            {"externalAgentId": "service-agent", "customFields": [
                {"sourceConnectionId": source.pk, "fieldId": second.config["fields"][0]["id"]}]}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_value_rows_have_postgres_tenant_guards_and_rls(self):
        source = self.source([{"key": "data", "label": "Data", "type": "string"}])
        row = self.value(source, "data", "private")
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
            self.assertFalse(ContactFieldValue.objects.filter(pk=row.pk).exists())
        with tenant_atomic(self.context), connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
            self.assertTrue(ContactFieldValue.objects.filter(pk=row.pk).exists())
