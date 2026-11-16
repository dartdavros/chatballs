"""Private test authority on real native models, with no external I/O."""

from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase

from chatballs.ai.external_agents import dispatch
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.ai.external_agents.test_models import ExternalAgentTestSession
from chatballs.conversations.models import Conversation, Message
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.tenancy.database import tenant_atomic


class ExternalTestScopeTests(RuntimeData, TestCase):
    def setUp(self):
        super().setUp()
        self.test_url = f"/api/v1/organizations/{self.organization.public_id}/agents/{self.channel.pk}/external-test/"

    def start_test(self, data=None):
        response = self.client.post(self.test_url, {"clientData": data or {}}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["id"]

    def test_private_pipeline_context_and_real_panel_publication_while_agent_paused(self):
        self.agent.status = "PAUSED"
        self.agent.save(update_fields=["status"])
        self.bind(self.connection.pk, standardFields=["name"])
        self.transport.reset_mock()
        with patch("chatballs.conversations.signals.notify_inbox_changed") as inbox, patch(
            "chatballs.conversations.signals.notify_conversation_changed") as realtime:
            identifier = self.start_test({"standardFields": {"name": "Explicit test name"}})
            response = self.client.post(self.test_url + identifier + "/", {"message": "Private question"}, format="json")
            self.assertEqual(response.status_code, 202, response.content)
            scope = ExternalAgentTestSession.objects.get(public_id=identifier)
            self.assertFalse(Conversation.objects.filter(pk=scope.conversation_id).exists())
            self.assertFalse(Message.objects.filter(conversation=scope.conversation).exists())
            self.assertIsNone(scope.conversation.contact_id)
            self.assertIsNone(scope.conversation.connection_id)
            row = ExternalAgentRequest.objects.get(conversation_id=scope.conversation_id)
            with tenant_atomic(self.context):
                self.assertIsNotNone(dispatch.claim(self.context, scope.conversation_id))
            row.refresh_from_db()
            snapshot = open_payload(row.snapshot_ciphertext)
            self.assertEqual(snapshot["context"]["customer"]["fields"], {"name": "Explicit test name"})
            self.assertEqual(snapshot["context"]["history"]["messages"], [])
            self.assertNotIn(self.contact.name, str(snapshot))
            response = self.callback(row, self.result(row, text="Private answer", count=2))
            self.assertEqual(response.status_code, 200, response.content)
            panel = self.client.get(self.test_url + identifier + "/").json()
            self.assertEqual(panel["state"], "ready")
            self.assertEqual([message["text"] for message in panel["messages"]], ["Private question", "Private answer", "Private answer"])
            inbox.assert_not_called()
            realtime.assert_not_called()
        self.transport.assert_not_called()
        self.sender.assert_not_called()
        ordinary = f"/api/v1/organizations/{self.organization.public_id}/conversations/{scope.conversation_id}/"
        self.assertEqual(self.client.get(ordinary).status_code, 404)

    def test_owner_scope_close_feature_gate_and_no_real_customer_data(self):
        response = self.client.post(self.test_url, {"clientData": {"standardFields": {"email": "private@example.invalid"}}}, format="json")
        self.assertEqual(response.status_code, 400)
        identifier = self.start_test()
        other = HumanUser.objects.create_user(email="other-test-admin@example.invalid")
        OrganizationMembership.objects.create(organization=self.organization, user=other, role="ADMIN")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(self.test_url + identifier + "/").status_code, 404)
        self.assertEqual(self.client.delete(self.test_url + identifier + "/").status_code, 404)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.delete(self.test_url + identifier + "/").status_code, 204)
        self.assertEqual(self.client.post(self.test_url + identifier + "/", {"message": "Closed"}, format="json").status_code, 400)
        self.client.patch(self.url, {"enabled": False}, format="json")
        self.assertEqual(self.client.post(self.test_url, {}, format="json").status_code, 400)
        self.assertEqual(self.client.get(self.test_url).status_code, 400)

    def test_restart_revokes_authority_and_audience_is_immutable(self):
        first = self.start_test()
        self.client.post(self.test_url + first + "/", {"message": "First"}, format="json")
        scope = ExternalAgentTestSession.objects.get(public_id=first)
        row = ExternalAgentRequest.objects.get(conversation=scope.conversation)
        with tenant_atomic(self.context):
            dispatch.claim(self.context, scope.conversation_id)
        self.start_test()
        self.assertEqual(self.callback(row, self.result(row)).json()["state"], "suppressed")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Conversation.including_tests.filter(pk=scope.conversation_id).update(is_test=False)
        self.assertEqual(Message.including_tests.filter(conversation_id=scope.conversation_id, author_type="AI").count(), 0)
