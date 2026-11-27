"""Значения формы при старте сессии используют запись и проверки setFields."""

from django.test import TestCase
from rest_framework.test import APIClient

from chatballs.ai.agent_card import ensure_channel_agent
from chatballs.channels.models import Channel
from chatballs.conversations.models import ContactFieldValue, Conversation
from chatballs.identity.models import Organization
from chatballs.webchat.models import WebSession
from chatballs.webchat.testing import create_web_widget


class PreChatSessionTests(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name="Form", slug="session-form")
        channel = Channel.objects.create(organization=organization, code="form", name="Form")
        self.widget = create_web_widget(channel)
        self.widget.integration.config = {
            "fields": [
                {"key": "order_id", "type": "string"}, {"key": "amount", "type": "number"},
                {"key": "confirmed", "type": "boolean"}, {"key": "when", "type": "datetime"},
                {"key": "status", "type": "enum", "options": [{"value": "new"}]},
            ],
            "preChat": {"enabled": True, "title": "", "fields": []},
        }
        self.widget.integration.save(update_fields=["config"])
        self.client = APIClient()

    def _session(self, **payload):
        response = self.client.post(
            "/api/v1/webchat/session/", {"widgetKey": self.widget.public_key, **payload}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        return WebSession.objects.latest("id")

    def _values(self, session):
        return dict(ContactFieldValue.objects.filter(contact=session.identity.contact).values_list("key", "value"))

    def test_agent_greeting_uses_saved_fields_without_active_ai(self):
        agent = ensure_channel_agent(self.widget.integration.channel)
        agent.greeting = "Здравствуйте, {{name}}! Заказ {{order_id}}."
        agent.save(update_fields=["greeting"])
        response = self.client.post("/api/v1/webchat/session/", {
            "widgetKey": self.widget.public_key,
            "consentVersion": "v1",
            "fields": {"name": "С сайта", "order_id": "42"},
            "preChatFields": {"name": "Андрей"},
        }, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['token']}")
        for _ in range(2):
            payload = self.client.get("/api/v1/webchat/messages/").json()
            self.assertEqual(payload["greeting"], "Здравствуйте, Андрей! Заказ 42.")
            self.assertFalse(payload["autonomous"])
        self.assertFalse(Conversation.objects.exists())

    def test_form_values_override_site_values_and_write_contact_and_custom_fields(self):
        session = self._session(
            fields={"name": "Site", "email": "site@example.test", "order_id": "site", "amount": 12},
            preChatFields={"name": "Client", "email": "client@example.test", "phone": "+7 (999) 123-45-67", "order_id": "form", "confirmed": False, "when": "2026-09-30T12:30", "status": "new"},
        )
        contact = session.identity.contact
        contact.refresh_from_db()
        self.assertEqual((contact.name, contact.email, contact.phone), ("Client", "client@example.test", "+79991234567"))
        self.assertEqual(self._values(session), {
            "name": "Client", "email": "client@example.test", "phone": "+79991234567",
            "order_id": "form", "amount": 12, "confirmed": False, "when": "2026-09-30T12:30", "status": "new",
        })
        self.assertFalse(Conversation.objects.filter(contact=contact).exists())

    def test_null_from_form_overrides_site_values(self):
        session = self._session(fields={"name": "Site", "order_id": "site"}, preChatFields={"name": None, "order_id": None})
        contact = session.identity.contact
        contact.refresh_from_db()
        self.assertEqual(contact.name, "")
        self.assertEqual(self._values(session), {})

    def test_invalid_form_values_use_same_validation_and_never_fall_back_to_site(self):
        valid = {"email": "site@example.test", "phone": "+79991234567", "order_id": "site", "amount": 10, "confirmed": True, "status": "new", "when": "2026-09-30T12:30"}
        invalid = {"email": "SECRET", "phone": "SECRET", "order_id": "SECRET" * 101, "amount": "SECRET", "confirmed": "SECRET", "status": "SECRET", "when": "SECRET", "unknown": "SECRET"}
        with self.assertLogs("chatballs.webchat.site_fields", level="WARNING") as logs:
            session = self._session(fields=valid, preChatFields=invalid)
        self.assertEqual(self._values(session), {})
        contact = session.identity.contact
        contact.refresh_from_db()
        self.assertEqual((contact.email, contact.phone), ("", ""))
        self.assertNotIn("SECRET", " ".join(logs.output))

    def test_invalid_payload_is_ignored_without_losing_valid_site_fields(self):
        with self.assertLogs("chatballs.webchat.site_fields", level="WARNING"):
            session = self._session(fields={"name": "Site"}, preChatFields=["SECRET"])
        self.assertEqual(self._values(session), {"name": "Site"})
        with self.assertLogs("chatballs.webchat.site_fields", level="WARNING"):
            session = self._session(fields=["SECRET"], preChatFields={"name": "Form"})
        self.assertEqual(self._values(session), {"name": "Form"})
