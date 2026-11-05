from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from chatballs.channels.models import Channel
from chatballs.conversations.models import Contact, Conversation, Message
from chatballs.identity.models import Organization
from chatballs.webchat.consent import has_current_consent, require_current_consent
from chatballs.webchat.models import WebSession
from chatballs.webchat.testing import create_web_widget


class ServerConsentTests(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name="Consent", slug="consent")
        channel = Channel.objects.create(organization=organization, code="consent", name="Consent")
        self.widget = create_web_widget(channel)
        self.widget.integration.config = {
            "preChat": {"enabled": True, "fields": [{"key": "email", "required": True}]},
        }
        self.widget.integration.save(update_fields=["config"])
        self.client = APIClient()

    def issue(self, **values):
        return self.client.post(
            "/api/v1/webchat/session/", {"widgetKey": self.widget.public_key, **values}, format="json",
        )

    def authorize(self, response):
        self.assertEqual(response.status_code, 201, response.content)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['token']}")

    def test_old_session_is_not_consent_and_explicit_acceptance_keeps_identity(self):
        response = self.issue()
        self.authorize(response)
        session = WebSession.objects.latest("id")
        self.assertFalse(has_current_consent(session))
        with self.assertRaises(ValidationError):
            require_current_consent(session)
        self.assertFalse(self.client.get("/api/v1/webchat/consent/").json()["accepted"])
        result = self.client.post("/api/v1/webchat/consent/", {
            "consentVersion": "v1", "preChatFields": {"email": "visitor@example.com"},
        }, format="json")
        self.assertEqual(result.status_code, 200, result.content)
        session.refresh_from_db()
        self.assertTrue(has_current_consent(session))
        require_current_consent(session)
        self.assertEqual(WebSession.objects.count(), 1)
        self.assertEqual(Contact.objects.count(), 1)
        self.assertFalse(Conversation.objects.exists())
        self.assertFalse(Message.objects.exists())

    def test_required_form_cannot_be_satisfied_by_site_fields_or_invalid_value(self):
        for form in (None, {}, {"email": ""}, {"email": "invalid"}, {"email": 1}):
            with self.subTest(form=form):
                response = self.issue(
                    consentVersion="v1", fields={"email": "site@example.com"}, preChatFields=form,
                )
                self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(WebSession.objects.exists())
        self.assertFalse(Contact.objects.exists())

    def test_current_form_is_accepted_and_policy_changes_invalidate_it(self):
        self.authorize(self.issue(consentVersion="v1", preChatFields={"email": "visitor@example.com"}))
        session = WebSession.objects.latest("id")
        self.assertTrue(has_current_consent(session))
        self.assertIsNotNone(session.consent_accepted_at)
        self.widget.consent_config = {"consent_version": "v2"}
        self.widget.save(update_fields=["consent_config"])
        self.assertFalse(self.client.get("/api/v1/webchat/consent/").json()["accepted"])
        result = self.client.post("/api/v1/webchat/consent/", {
            "consentVersion": "v1", "preChatFields": {"email": "visitor@example.com"},
        }, format="json")
        self.assertEqual(result.status_code, 400)
        self.widget.consent_config = {}
        self.widget.save(update_fields=["consent_config"])
        self.widget.integration.config["preChat"]["fields"].append({"key": "phone", "required": True})
        self.widget.integration.save(update_fields=["config"])
        self.assertFalse(self.client.get("/api/v1/webchat/consent/").json()["accepted"])

    def test_unpublished_widget_and_disallowed_origin_cannot_accept(self):
        self.authorize(self.issue())
        self.widget.allowed_origins = ["https://allowed.example"]
        self.widget.save(update_fields=["allowed_origins"])
        result = self.client.post("/api/v1/webchat/consent/", {
            "consentVersion": "v1", "preChatFields": {"email": "visitor@example.com"},
        }, format="json", HTTP_ORIGIN="https://other.example")
        self.assertEqual(result.status_code, 401)
        self.widget.allowed_origins = []
        self.widget.status = "DISABLED"
        self.widget.save(update_fields=["allowed_origins", "status"])
        self.assertEqual(self.client.get("/api/v1/webchat/consent/").status_code, 401)
