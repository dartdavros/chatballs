"""Affected tenant, transport and public projection boundaries in the test DB."""

from unittest.mock import patch
from uuid import uuid4

from django.db import connection, transaction
from django.test import TestCase

from chatballs.ai.external_agents import test_chat
from chatballs.ai.external_agents.handoff import handoff
from chatballs.ai.external_agents.notice_models import ExternalAgentNotice
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.ai.external_agents.test_models import ExternalAgentTestSession
from chatballs.ai.external_agents.ui_projection import conversation_status
from chatballs.ai.models import Skill
from chatballs.ai.template_runtime_testing import reply_template
from chatballs.conversations.diagnostic_export import conversation_diagnostic
from chatballs.conversations.models import Message
from chatballs.conversations.serializers import message_payload
from chatballs.identity.models import Organization
from chatballs.tenancy.database import tenant_atomic


class SettingsSecurityTests(RuntimeData, TestCase):
    def test_test_scope_does_not_change_agent_or_channel_counters(self):
        from chatballs.ai.agent_card import agent_cards_for_context
        from chatballs.channels.selectors import channels_for_context

        scope_id = test_chat.start(self.context, self.channel.pk, {})["id"]
        test_chat.send(self.context, self.channel.pk, scope_id, {"message": "Private test"})
        with tenant_atomic(self.context):
            self.assertEqual(agent_cards_for_context(self.context).get(pk=self.channel.pk).open_conversations_count, 1)
            self.assertEqual(channels_for_context(self.context).get(pk=self.channel.pk).open_conversations_count, 1)
            self.assertEqual(Message.objects.count(), 0)

    def test_new_test_and_notice_tables_obey_runtime_rls(self):
        scope_id = test_chat.start(self.context, self.channel.pk, {})["id"]
        foreign = Organization.objects.create(name="Foreign", slug="test-scope-foreign")
        with tenant_atomic(self.context):
            handoff(self.conversation, self.context, operation_id=uuid4(), summary="Business summary")
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
            try:
                self.assertEqual(ExternalAgentTestSession.objects.count(), 0)
                self.assertEqual(ExternalAgentNotice.objects.count(), 0)
            finally:
                cursor.execute("RESET ROLE")
        with tenant_atomic(self.context), connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
            try:
                self.assertEqual(str(ExternalAgentTestSession.objects.get().public_id), scope_id)
                self.assertEqual(ExternalAgentNotice.objects.count(), 1)
                self.assertFalse(ExternalAgentTestSession.objects.filter(organization=foreign).exists())
            finally:
                cursor.execute("RESET ROLE")

    def test_old_test_chat_cannot_export_through_builtin(self):
        self.transport.reset_mock()
        with patch("chatballs.ai.test_chat_service.plan_query_embedding") as plan:
            response = self.client.post(f"/api/v1/organizations/{self.organization.public_id}/agents/{self.channel.pk}/test-chat/",
                                        {"message": "Question"}, format="json")
        self.assertEqual(response.status_code, 400, response.content)
        plan.assert_not_called()
        self.transport.assert_not_called()

    def test_partial_projection_and_handoff_never_read_recovery_or_expose_credentials(self):
        row = self.request()
        self.claim()
        self.callback(row, self.result(row, count=2))
        self.sender.side_effect = [True, False]
        self.deliver(times=2)
        with tenant_atomic(self.context):
            state = conversation_status(self.conversation)
            self.assertEqual(state["notices"][-1]["kind"], "partial")
            messages = [message_payload(message) for message in Message.objects.filter(author_type="AI").order_by("pk")]
            self.assertEqual([message["externalDelivery"]["state"] for message in messages], ["transport_accepted", "unknown"])
            handoff(self.conversation, self.context, operation_id=uuid4(), summary="Business outbound-test-secret Bearer private-token")
            self.assertNotIn("outbound-test-secret", ExternalAgentNotice.objects.get().summary)
            self.assertNotIn("private-token", ExternalAgentNotice.objects.get().summary)
            export = str(conversation_diagnostic(self.conversation))
            for value in ("seed_ciphertext", "snapshot_ciphertext", "history_ciphertext", "outbound-test-secret", "private-token"):
                self.assertNotIn(value, export)
            self.assertEqual(conversation_diagnostic(self.conversation)["turns"], [])

    def test_template_preview_is_current_own_org_example_only(self):
        template = reply_template()
        template["examples"] = [{"title": "Saved example", "amount": 0, "active": False}]
        Skill.objects.create(organization=self.organization, name="Own", description="Own", instruction="PRIVATE", templates=[template])
        response = self.client.get(self.url + f'templates/{template["id"]}/preview/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("Saved example", response.json()["text"])
        self.assertNotIn("PRIVATE", str(response.json()))
        foreign = Organization.objects.create(name="Foreign", slug="template-preview-foreign")
        template["id"] = str(uuid4())
        Skill.objects.create(organization=foreign, name="Foreign", description="Private", instruction="PRIVATE", templates=[template])
        self.assertEqual(self.client.get(self.url + f'templates/{template["id"]}/preview/').status_code, 404)
