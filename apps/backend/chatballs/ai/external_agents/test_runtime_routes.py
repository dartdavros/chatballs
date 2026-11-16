"""WEB publication and factual SMTP outcomes through the existing transports."""

from unittest.mock import patch

from django.test import TestCase

from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.conversations.models import ConnectionIdentity, Message
from chatballs.conversations.transports.email_smtp import MailOutcome
from chatballs.integrations.models import Integration
from chatballs.webchat.consent import current_version, record_acceptance
from chatballs.webchat.models import WebSession
from chatballs.webchat.testing import create_web_widget


class RuntimeRouteTests(RuntimeData, TestCase):
    def web(self):
        self.organization.refresh_from_db()
        self.channel.organization = self.organization
        widget = create_web_widget(self.channel)
        widget.consent_config = {"consent_text": "External execution consent in test DB", "consent_version": "v2"}
        widget.save(update_fields=["consent_config"])
        self.conversation.connection = widget.integration
        self.conversation.save(update_fields=["connection"])
        identity = ConnectionIdentity.objects.create(contact=self.contact, connection=widget.integration,
                                                     external_user_id="web-test")
        session = WebSession.objects.create(connection=widget.integration, identity=identity, widget=widget,
                                             token_hash="c" * 64)
        # Reload all disclosure generations after changing the conversation route.
        session = WebSession.objects.select_related("widget__integration__channel__ai_agent").get(pk=session.pk)
        record_acceptance(session, version=current_version(session.widget), fields={})
        return widget

    def test_web_publishes_once_after_guard_and_needs_no_network_delivery(self):
        self.web()
        row = self.request()
        self.assertIsNotNone(self.claim())
        result = self.result(row)
        response = self.callback(row, result)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["state"], "transport_accepted")
        self.deliver()
        self.sender.assert_not_called()
        self.assertEqual(Message.objects.filter(author_type="AI").count(), 1)
        self.assertEqual(self.callback(row, result).json(), response.json())

    def test_changed_web_consent_suppresses_before_any_public_row(self):
        widget = self.web()
        row = self.request()
        self.claim()
        widget.consent_config = {"consent_text": "New disclosure", "consent_version": "v3"}
        widget.save(update_fields=["consent_config"])
        response = self.callback(row, self.result(row))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["state"], "suppressed")
        self.assertFalse(Message.objects.filter(author_type="AI").exists())

    def test_smtp_rejection_is_failed_and_keeps_saved_route_and_message_id(self):
        mailbox = Integration.objects.create(organization=self.organization, channel=self.channel,
            kind="MESSENGER", provider="EMAIL", name="Mail", secret="test-password",
            config={"email": "support@example.invalid", "smtp_host": "mail.example.invalid"})
        self.conversation.connection, self.conversation.external_chat_id = mailbox, "customer@example.invalid"
        self.conversation.transport_meta = {"subject": "Question", "last_message_id": "<incoming@example.invalid>"}
        self.conversation.save(update_fields=["connection", "external_chat_id", "transport_meta"])
        row = self.request()
        self.claim()
        self.accept(row, self.result(row))
        with patch("chatballs.ai.external_agents.delivery.deliver_message", return_value=MailOutcome("FAILED", "SMTP_REJECTED")) as smtp:
            self.deliver()
        self.assertEqual(smtp.call_count, 1)
        outgoing = smtp.call_args.args[1]
        self.assertEqual(outgoing["To"], "customer@example.invalid")
        self.assertEqual(outgoing["In-Reply-To"], "<incoming@example.invalid>")
        self.assertTrue(outgoing["Message-ID"])
        self.assertEqual(ExternalAgentDeliveryItem.objects.get().state, "failed")
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.control_mode, "PAUSED")
