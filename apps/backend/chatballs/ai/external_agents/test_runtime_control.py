"""Control loss, scope isolation and explicit unsupported-content rejection."""

from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase

from chatballs.ai.external_agents import history
from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.conversations.models import Message
from chatballs.tenancy.database import tenant_atomic


class RuntimeControlTests(RuntimeData, TestCase):
    def test_each_control_transition_suppresses_late_authenticated_callback(self):
        for field, value in (("control_mode", "HUMAN"), ("lifecycle", "CLOSED"), ("assigned_operator", self.user)):
            with self.subTest(field=field):
                row = self.request()
                self.claim()
                setattr(self.conversation, field, value)
                self.conversation.save(update_fields=[field])
                response = self.callback(row, self.result(row))
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(response.json()["state"], "suppressed")
                self.assertFalse(Message.objects.filter(author_type="AI").exists())
                setattr(self.conversation, field, "AI" if field == "control_mode" else "OPEN" if field == "lifecycle" else None)
                self.conversation.save(update_fields=[field])

    def test_feature_disable_preserves_configuration_and_old_authority_never_revives(self):
        row = self.request()
        self.claim()
        for enabled in (False, True):
            self.client.patch(self.url, {"enabled": enabled}, format="json")
        response = self.callback(row, self.result(row))
        self.assertEqual(response.json()["state"], "suppressed")
        self.assertTrue(self.client.get(self.url).json()["connections"])
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.execution_mode, "external")
        self.assertFalse(self.client.get(self.url).json()["connections"][0]["compatible"])
        checked = self.client.post(self.url + f"connections/{self.connection.pk}/check/", {}, format="json")
        self.assertEqual(checked.status_code, 200, checked.content)
        self.bind(self.connection.pk)
        fresh = self.request("new turn")
        self.assertNotEqual(row.authorization_id, fresh.authorization_id)

    def test_key_rotation_rejects_revoked_key_and_wrong_connection(self):
        row = self.request()
        self.claim()
        url = f"/api/v1/external-agent/connections/{self.connection.pk + 1}/requests/{row.public_id}/result/"
        result = self.result(row)
        response = self.client.post(url, result, format="json", HTTP_AUTHORIZATION="Bearer " + self.created["incomingKey"])
        self.assertEqual(response.status_code, 404)
        self.client.post(self.url + f"connections/{self.connection.pk}/key/", {}, format="json")
        self.assertEqual(self.callback(row, result).status_code, 401)

    def test_takeover_before_send_suppresses_remaining_items(self):
        row = self.request()
        self.claim()
        self.accept(row, self.result(row, count=2))
        self.deliver(times=1)
        self.conversation.control_mode = "HUMAN"
        self.conversation.save(update_fields=["control_mode"])
        self.deliver(times=2)
        self.assertEqual(list(ExternalAgentDeliveryItem.objects.values_list("state", flat=True)), ["transport_accepted", "suppressed"])
        self.assertEqual(self.sender.call_count, 1)

    def test_web_guard_precedes_publication(self):
        row = self.request()
        self.claim()
        with patch("chatballs.ai.external_agents.readiness.consent_current", return_value=False):
            response = self.callback(row, self.result(row))
        self.assertEqual(response.json()["state"], "suppressed")
        self.assertFalse(Message.objects.filter(author_type="AI").exists())

    def test_history_snapshot_excludes_trigger_future_and_internal_records(self):
        for i in range(24):
            Message.objects.create(conversation=self.conversation, author_type="OPERATOR", text=f"prior-{i}")
        Message.objects.create(conversation=self.conversation, author_type="SYSTEM", text="Private event")
        row = self.request()
        self.request("future trigger")
        self.claim()
        row.refresh_from_db()
        snapshot = open_payload(row.snapshot_ciphertext)
        page_query = {"authorizationId": str(row.authorization_id),
                      "snapshotCursor": snapshot["context"]["history"]["snapshotCursor"],
                      "pageCursor": snapshot["context"]["history"]["nextCursor"], "pageSize": "3"}
        with tenant_atomic(self.context):
            page = history.read(self.context, self.connection, self.conversation.pk, page_query)
        self.assertEqual([item["content"]["text"] for item in page["items"]], ["prior-1", "prior-2", "prior-3"])
        self.assertTrue(page["hasMore"])
        self.assertTrue(snapshot["context"]["history"]["truncated"])
        self.assertEqual(page["snapshotCursor"], page_query["snapshotCursor"])

    def test_unknown_cancelled_and_unsupported_outcome_are_not_terminal_results(self):
        row = self.request()
        self.claim()
        for status in ("unknown", "cancelled"):
            body = {"version": "1", "requestId": str(row.public_id), "status": status,
                    "externalSessionId": None, "reasonCode": "service_failed"}
            self.assertEqual(self.callback(row, body).status_code, 400)
        body = self.result(row)
        changed = deepcopy(body)
        changed["outcome"]["messages"][0]["content"] = {"type": "contact", "text": "not an outgoing command"}
        self.assertEqual(self.callback(row, changed).status_code, 400)
        self.assertFalse(Message.objects.filter(author_type="AI").exists())
