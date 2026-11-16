from chatballs.ai.external_agents.config_bindings import select_execution
from chatballs.ai.external_agents.readiness import consent_current
from chatballs.ai.external_agents.testing import ConfigurationCase
from chatballs.conversations.models import ConnectionIdentity, Contact, Conversation
from chatballs.webchat.consent import current_version, record_acceptance
from chatballs.webchat.models import WebSession
from chatballs.webchat.testing import create_web_widget


class ExternalConsentTests(ConfigurationCase):
    def test_public_disclosure_uses_server_version_custom_terms_and_escaped_service_name(self):
        from rest_framework.exceptions import ValidationError

        from chatballs.ai.external_agents.config_models import ExternalAgentConnection
        from chatballs.webchat.configuration import public_config
        from chatballs.webchat.consent import validate_acceptance
        from chatballs.webchat.models import WebChatWidget

        select_execution(self.context, self.agent.pk, "external")
        service = ExternalAgentConnection.objects.get(pk=self.identifier).integration
        service.name = "Service <script>private</script>"
        service.save(update_fields=["name"])
        self.widget.consent_config = {"consent_text": "<p>Existing terms</p><script>bad</script>", "consent_version": "custom"}
        self.widget.save(update_fields=["consent_config"])
        widget = WebChatWidget.objects.get(pk=self.widget.pk)
        payload = public_config(context=self.context, widget=widget, origin="https://example.invalid")["consent"]
        self.assertIn("Existing terms", payload["text"])
        self.assertIn("в исходном виде", payload["text"])
        self.assertIn("Исходная аудиозапись этому сервису не передаётся", payload["text"])
        self.assertIn("&lt;script&gt;", payload["text"])
        self.assertNotIn("<script>", payload["text"])
        self.assertNotIn("outbound-test-secret", payload["text"])
        self.assertEqual(payload["version"], current_version(widget))
        self.assertNotEqual(payload["version"], "custom")
        self.assertRaises(ValidationError, validate_acceptance, widget, "custom", {})
        validate_acceptance(widget, payload["version"], {})

    def setUp(self):
        super().setUp()
        self.created = self.connect()
        self.identifier = self.created["connection"]["id"]
        self.bind(self.identifier)
        self.widget = create_web_widget(self.channel)
        self.widget.consent_config = {"consent_text": "Consent recorded in the isolated test", "consent_version": "v2"}
        self.widget.save(update_fields=["consent_config"])
        contact = Contact.objects.create(organization=self.organization, name="Customer")
        identity = ConnectionIdentity.objects.create(contact=contact, connection=self.widget.integration,
                                                     external_user_id="test-visitor")
        self.session = WebSession.objects.create(connection=self.widget.integration, identity=identity,
                                                 widget=self.widget, token_hash="a" * 64)
        self.conversation = Conversation.objects.create(organization=self.organization, channel=self.channel,
                                                       connection=self.widget.integration, contact=contact)
        self.accept()

    def accept(self):
        self.session.refresh_from_db()
        record_acceptance(self.session, version=current_version(self.session.widget), fields={})

    def test_external_mode_and_policy_need_new_server_consent(self):
        self.assertTrue(consent_current(self.conversation))
        select_execution(self.context, self.agent.pk, "external")
        self.assertFalse(consent_current(self.conversation))
        self.accept()
        self.assertTrue(consent_current(self.conversation))
        self.bind(self.identifier, standardFields=["email"])
        self.assertFalse(consent_current(self.conversation))
        self.accept()
        self.assertTrue(consent_current(self.conversation))

    def test_other_contact_consent_and_default_text_do_not_authorize_export(self):
        select_execution(self.context, self.agent.pk, "external")
        self.accept()
        other = Contact.objects.create(organization=self.organization, name="Other")
        conversation = Conversation.objects.create(organization=self.organization, channel=self.channel,
                                                    connection=self.widget.integration, contact=other)
        self.assertFalse(consent_current(conversation))
        self.widget.consent_config = {"consent_version": "v2"}
        self.widget.save(update_fields=["consent_config"])
        self.assertFalse(consent_current(self.conversation))

    def test_allowed_source_schema_roundtrip_invalidates_actual_saved_web_form(self):
        from copy import deepcopy

        from chatballs.integrations.models import Integration
        from chatballs.webchat.field_schema import normalize_fields

        source = Integration.objects.create(organization=self.organization, name="Allowed source",
            provider="WEB", kind="MESSENGER", config={"fields": normalize_fields([
                {"key": "state", "label": "State", "type": "string"}], [])})
        self.bind(self.identifier, customFields=[{
            "sourceConnectionId": source.pk, "fieldId": source.config["fields"][0]["id"]}])
        select_execution(self.context, self.agent.pk, "external")
        self.accept()
        self.assertTrue(consent_current(self.conversation))
        original = deepcopy(source.config)
        source.config["fields"][0]["label"] = "Changed"
        source.save(update_fields=["config"])
        source.config = original
        source.save(update_fields=["config"])
        self.assertFalse(consent_current(self.conversation))
        self.accept()
        self.assertTrue(consent_current(self.conversation))
