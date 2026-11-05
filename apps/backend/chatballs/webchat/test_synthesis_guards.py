import io
import wave
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from chatballs.ai.models import AIAgent
from chatballs.channels.models import Channel
from chatballs.conversations.models import Contact, Conversation, Message
from chatballs.identity.models import Organization
from chatballs.integrations.models import Integration
from chatballs.speech.agent_configuration import configure_agent_synthesis
from chatballs.speech.synthesis import resolve_synthesis
from chatballs.tenancy.context import TenantContext
from chatballs.webchat.models import WebSession
from chatballs.webchat.speech_selectors import synthesis_message
from chatballs.webchat.testing import create_web_widget


class SynthesisGuardTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Synthesis", slug="synthesis", operation_mode="AI_AGENTS")
        self.channel = Channel.objects.create(organization=self.organization, name="Synthesis", code="synthesis")
        text_provider = Integration.objects.create(organization=self.organization, name="Text", kind="LLM_PROVIDER",
                                                   provider="DEMO", secret="unit-test-never-sent", status="OK")
        self.provider = Integration.objects.create(organization=self.organization, name="Speech", kind="SPEECH_PROVIDER",
                                                  provider="YANDEX_SPEECHKIT", secret="unit-test-never-sent",
                                                  config={"folder_id": "unit-test"}, status="OK")
        self.agent = AIAgent.objects.create(channel=self.channel, name="Synthesis", status="ACTIVE",
                                           provider_integration=text_provider, synthesis_integration=self.provider,
                                           synthesis_voice="alena")
        self.widget = create_web_widget(self.channel)
        self.connection = self.widget.integration
        self.connection.config = {"answerPlaybackEnabled": True}
        self.connection.save(update_fields=["config"])
        self.client = APIClient()
        self.issue(consent=True)
        self.session = WebSession.objects.latest("id")
        self.conversation = Conversation.objects.create(organization=self.organization, channel=self.channel,
                                                        connection=self.connection, contact=self.session.identity.contact)
        self.message = Message.objects.create(conversation=self.conversation, author_type="AI",
                                             text="Здравствуйте! Спасибо за обращение. Срок пошива составляет пять рабочих дней.")
        self.revision = resolve_synthesis(self.connection)[1]

    def issue(self, consent):
        response = self.client.post("/api/v1/webchat/session/", {
            "widgetKey": self.widget.public_key, **({"consentVersion": "v1"} if consent else {}),
        }, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['token']}")

    def post(self, message=None, **body):
        return self.client.post(f"/api/v1/webchat/messages/{(message or self.message).id}/synthesis/",
                                {"revision": self.revision, **body}, format="json")

    def assert_rejected(self, message=None, **body):
        # This assertion prevents accidental external traffic in access tests.
        with patch("chatballs.speech.providers.yandex_tts.YandexTTS.synthesize", side_effect=AssertionError("guard leaked")) as synthesize:
            response = self.post(message, **body)
        self.assertIn(response.status_code, (400, 401, 429), response.content)
        synthesize.assert_not_called()

    def synthesize(self, before_return=lambda: None):
        with io.BytesIO() as output:
            with wave.open(output, "wb") as audio:
                audio.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
                audio.writeframes(b"\0\0")
            wav = output.getvalue()

        def complete(text):
            self.assertEqual(text, self.message.text)
            before_return()
            return wav

        with patch("chatballs.speech.providers.yandex_tts.YandexTTS.synthesize", side_effect=complete) as provider:
            response = self.post()
        provider.assert_called_once_with(self.message.text)
        return response, wav

    def test_synthesis_uses_plain_snapshot_without_changing_history(self):
        self.message.format_version = 1
        self.message.content_html = "<h3>Display only</h3><style>body{color:red}</style>"
        self.message.presentation = {"instructions": "not spoken"}
        self.message.save()
        before = list(Message.objects.values("id", "text", "content_html", "presentation"))
        response, wav = self.synthesize()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response["Content-Type"], "audio/wav")
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response.content, wav)
        self.assertEqual(list(Message.objects.values("id", "text", "content_html", "presentation")), before)

    def test_consent_change_during_synthesis_prevents_audio_delivery(self):
        def revoke():
            self.widget.consent_config = {"consent_version": "v2"}
            self.widget.save(update_fields=["consent_config"])

        response, _ = self.synthesize(revoke)
        self.assertEqual(response.status_code, 400, response.content)
        self.assertNotEqual(response["Content-Type"], "audio/wav")

    def test_configuration_change_during_synthesis_prevents_audio_delivery(self):
        def change_voice():
            self.agent.synthesis_voice = "john"
            self.agent.save(update_fields=["synthesis_voice", "updated_at"])

        response, _ = self.synthesize(change_voice)
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()["code"], "tts_changed")

    def test_only_stored_customer_ai_text_is_selected(self):
        self.message.format_version = 1
        self.message.content_html = "<p>Do not synthesize HTML</p><style>secret</style>"
        self.message.presentation = {"instructions": "never synthesize"}
        self.message.save()
        self.assertEqual(synthesis_message(self.session, self.message.id).text, self.message.text)
        incoming = Message.objects.create(conversation=self.conversation, author_type="CONTACT", text="Question")
        for values in ({"author_type": "OPERATOR"}, {"author_type": "CONTACT"}, {"author_type": "SYSTEM"},
                       {"author_type": "AI", "kind": "voice"}, {"author_type": "AI", "system_event": "tool_call"},
                       {"author_type": "AI", "ai_turn_state": "RUNNING"},
                       {"author_type": "AI", "ai_reply_to": incoming, "ai_delivery": {"sent": False}}):
            message = Message.objects.create(conversation=self.conversation, text="private", **values)
            with self.subTest(values=values):
                self.assert_rejected(message)
        self.assert_rejected(text="arbitrary browser text")

    def test_other_contact_connection_and_organization_are_inaccessible(self):
        other_contact = Contact.objects.create(organization=self.organization, name="Other")
        other_connection = create_web_widget(self.channel, name="Other widget").integration
        other_org = Organization.objects.create(name="Other", slug="other-synthesis")
        other_channel = Channel.objects.create(organization=other_org, name="Other", code="other")
        other_customer = Contact.objects.create(organization=other_org, name="Other organization")
        for values in ({"contact": other_contact}, {"connection": other_connection},
                       {"organization": other_org, "channel": other_channel, "connection": None, "contact": other_customer}):
            params = {"organization": self.organization, "channel": self.channel, "connection": self.connection,
                      "contact": self.session.identity.contact, **values}
            conversation = Conversation.objects.create(**params)
            message = Message.objects.create(conversation=conversation, author_type="AI", text="private")
            self.assert_rejected(message)

    def test_consent_required_form_origin_and_publication_are_checked(self):
        self.issue(consent=False)
        self.assert_rejected()
        self.issue(consent=True)
        self.widget.allowed_origins = ["https://allowed.example"]
        self.widget.save(update_fields=["allowed_origins"])
        self.assert_rejected(hostOrigin="https://other.example")
        self.widget.allowed_origins = []
        self.widget.status = "DISABLED"
        self.widget.save(update_fields=["allowed_origins", "status"])
        self.assert_rejected()

    def test_current_consent_and_settings_revision_are_enforced(self):
        playback = self.client.get("/api/v1/webchat/messages/").json()["playback"]
        self.assertTrue(playback["consentCurrent"])
        self.assertTrue(playback["playbackAvailable"])
        self.assert_rejected(revision="outdated")
        self.widget.consent_config = {"consent_version": "v2"}
        self.widget.save(update_fields=["consent_config"])
        self.assert_rejected()
        playback = self.client.get("/api/v1/webchat/messages/").json()["playback"]
        self.assertFalse(playback["consentCurrent"])
        self.assertFalse(playback["playbackAvailable"])
        self.widget.consent_config = {}
        self.widget.save(update_fields=["consent_config"])
        self.connection.config["preChat"] = {"enabled": True, "fields": [{"key": "email", "required": True}]}
        self.connection.save(update_fields=["config"])
        self.assert_rejected()

    def test_empty_selection_disables_without_inheritance_and_configuration_is_tenant_scoped(self):
        self.agent.synthesis_integration = None
        self.agent.save()
        self.assert_rejected()
        self.agent.synthesis_integration = self.provider
        self.agent.synthesis_voice = ""
        self.agent.save()
        self.assert_rejected()
        other_org = Organization.objects.create(name="Other", slug="other-config")
        with self.assertRaises(ValidationError) as error:
            configure_agent_synthesis(TenantContext.for_resource(other_org), self.agent,
                                      integration_id=self.provider.id, model="", voice="alena")
        self.assertIn("synthesisIntegrationId", str(error.exception))

    def test_operator_only_mode_and_disabled_web_function_stop_synthesis(self):
        self.organization.operation_mode = "OPERATORS_ONLY"
        self.organization.save(update_fields=["operation_mode"])
        self.assert_rejected()
        self.organization.operation_mode = "AI_AGENTS"
        self.organization.save(update_fields=["operation_mode"])
        self.connection.config = {"answerPlaybackEnabled": False}
        self.connection.save(update_fields=["config"])
        self.assert_rejected()
