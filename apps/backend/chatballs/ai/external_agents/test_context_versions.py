"""Immutable retries, native definition transactions and non-revivable policy."""

from copy import deepcopy

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from chatballs.ai.external_agents import history
from chatballs.ai.external_agents.auth import authorize_session
from chatballs.ai.external_agents.context_testing import ContextData
from chatballs.ai.external_agents.custom_field_revisions import fingerprint
from chatballs.ai.external_agents.custom_fields import snapshot
from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.send_guards import request_current
from chatballs.conversations.models import ContactFieldValue
from chatballs.events.models import OutboxEvent
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat.site_fields import save_site_fields


class ContextVersionTests(ContextData, TestCase):
    def setUp(self):
        super().setUp()
        self.web = self.source([{"key": "state", "label": "State", "type": "string"}])
        self.grant(self.web, standard=("name", "email"))
        self.value_row = self.value(self.web, "state", "before")

    def test_retry_restart_freezes_all_fields_and_next_turn_reads_fresh(self):
        row = self.request()
        first = self.claim()
        before = self.frozen(row)
        original_digest = row.snapshot_digest
        self.value_row.value = "after"
        self.value_row.save()
        self.contact.name = "Fresh name"
        self.contact.save()
        self.settle(first)
        ExternalAgentRequest.objects.filter(pk=row.pk).update(next_at=timezone.now())
        retry = self.claim()
        self.assertEqual(retry.request.body, first.request.body)
        self.assertEqual(self.frozen(row), before)
        self.assertEqual(row.snapshot_digest, original_digest)
        self.accept(row, self.result(row))
        self.deliver()
        fresh = self.request("next")
        self.claim()
        customer = self.frozen(fresh)["context"]["customer"]
        self.assertEqual(customer["fields"]["name"], "Fresh name")
        self.assertEqual(customer["customFields"]["items"][0]["value"], "after")
        self.assertNotEqual(customer["customFields"]["snapshotId"], before["context"]["customer"]["customFields"]["snapshotId"])
        self.assertEqual(self.callback(row, self.result(row)).status_code, 409)

    def test_native_schema_a_b_a_revokes_request_cursor_and_delivery(self):
        row = self.request()
        work = self.claim()
        query = {"authorizationId": str(row.authorization_id),
                 "snapshotCursor": self.frozen(row)["context"]["history"]["snapshotCursor"]}
        self.accept(row, self.result(row))
        original = deepcopy(self.schema_payload(self.web))
        initial_generation = self.web.web_schema_generation
        original_fingerprint = fingerprint(self.binding())
        changed = deepcopy(original)
        changed[0]["label"] = "Changed"
        self.change_schema(self.web, changed)
        self.change_schema(self.web, original)
        self.assertEqual(self.web.config["fields"][0]["label"], "State")
        self.assertEqual(self.web.web_schema_generation, initial_generation + 2)
        self.assertNotEqual(fingerprint(self.binding()), original_fingerprint)
        self.assertFalse(request_current(work, self.context))
        with self.assertRaises(PermissionDenied), tenant_atomic(self.context):
            history.read(self.context, self.connection, self.conversation.pk, query)
        self.deliver(times=1)
        self.sender.assert_not_called()
        self.assertEqual(ExternalAgentDeliveryItem.objects.get().state, "suppressed")

    def test_delete_recreate_never_inherits_id_or_exports_orphan_rows(self):
        original = self.schema_payload(self.web)
        old_id = original[0]["id"]
        self.change_schema(self.web, [])
        self.assertEqual(snapshot(self.binding(), self.contact)["items"], [])
        self.assertTrue(ContactFieldValue.objects.filter(pk=self.value_row.pk).exists())
        self.change_schema(self.web, original)
        self.assertNotEqual(self.web.config["fields"][0]["id"], old_id)
        self.assertEqual(snapshot(self.binding(), self.contact)["scope"], [])
        self.assertEqual(self.binding().custom_fields[0]["fieldId"], old_id)

    def test_source_and_allowlist_revocation_never_reanimate_authority(self):
        row = self.request()
        work = self.claim()
        self.web.refresh_from_db()
        for enabled in (False, True):
            self.web.is_active = enabled
            self.web.save(update_fields=["is_active"])
        self.assertFalse(request_current(work, self.context))
        with self.assertRaises(PermissionDenied), tenant_atomic(self.context):
            authorize_session(self.context, self.connection, conversation_id=self.conversation.pk,
                              authorization_id=row.authorization_id, operation="messages")
        self.grant()
        self.grant(self.web, standard=("name", "email"))
        self.assertEqual(self.callback(row, self.result(row)).json()["state"], "suppressed")

    def test_value_change_does_not_dispatch_or_advance_schema_and_invalid_never_leaks(self):
        before_generation = self.web.web_schema_generation
        before = fingerprint(self.binding())
        events = OutboxEvent.objects.count()
        self.value_row.value = "after"
        self.value_row.save()
        self.web.refresh_from_db()
        self.assertEqual(self.web.web_schema_generation, before_generation)
        self.assertEqual(fingerprint(self.binding()), before)
        self.assertEqual(OutboxEvent.objects.count(), events)
        self.assertFalse(ExternalAgentRequest.objects.exists())

    def test_native_site_value_update_and_clear_do_not_enqueue_external_work(self):
        from types import SimpleNamespace

        session = SimpleNamespace(identity=SimpleNamespace(contact_id=self.contact.pk),
                                  organization_id=self.organization.pk, connection=self.web)
        events = OutboxEvent.objects.filter(event_type="external_agent.wake").count()
        save_site_fields(session, {"state": "updated"})
        self.assertEqual(snapshot(self.binding(), self.contact)["items"][0]["value"], "updated")
        save_site_fields(session, {"state": None})
        item = snapshot(self.binding(), self.contact)["items"][0]
        self.assertEqual((item["status"], item["value"], item["updatedAt"]), ("unset", None, None))
        self.assertEqual(OutboxEvent.objects.filter(event_type="external_agent.wake").count(), events)
        self.assertFalse(ExternalAgentRequest.objects.exists())

    def test_type_and_enum_options_change_revalidates_stored_values(self):
        schema = self.schema_payload(self.web)
        schema[0].update(type="enum", options=[{"value": "before", "label": "Before"}])
        self.change_schema(self.web, schema)
        self.assertEqual(snapshot(self.binding(), self.contact)["items"][0]["status"], "set")
        schema[0]["options"] = [{"value": "other", "label": "Other"}]
        self.change_schema(self.web, schema)
        item = snapshot(self.binding(), self.contact)["items"][0]
        self.assertEqual((item["status"], item["value"], item["reasonCode"]), ("invalid", None, "option"))
        self.assertEqual(item["options"], schema[0]["options"])
        schema[0].update(type="boolean", options=[])
        self.change_schema(self.web, schema)
        self.assertEqual(snapshot(self.binding(), self.contact)["items"][0]["reasonCode"], "type")

    def test_employee_return_uses_fresh_snapshot_and_old_callback_cannot_replace_it(self):
        from chatballs.conversations.control_services import claim_conversation, release_to_ai

        row = self.request()
        self.claim()
        result = self.result(row)
        ack = self.callback(row, result)
        claim_conversation(context=self.context, conversation_id=self.conversation.pk)
        self.deliver(times=1)
        self.value_row.value = "employee-updated"
        self.value_row.save()
        with tenant_atomic(self.context):
            release_to_ai(context=self.context, conversation_id=self.conversation.pk)
        fresh = self.request("after employee")
        self.assertIsNotNone(self.claim())
        before = self.frozen(fresh)
        self.assertNotEqual(row.authorization_id, fresh.authorization_id)
        self.assertEqual(before["context"]["customer"]["customFields"]["items"][0]["value"], "employee-updated")
        repeated = self.callback(row, result)
        self.assertEqual(repeated.json(), ack.json())
        self.assertEqual(self.frozen(fresh), before)
