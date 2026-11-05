from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from chatballs.ai.models import AIAgent
from chatballs.channels.models import Channel
from chatballs.conversations.models import Conversation, Message
from chatballs.identity.models import Organization
from chatballs.integrations.models import Integration
from chatballs.webchat.testing import create_web_widget


class DictationGuardTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Speech", slug="speech")
        self.channel = Channel.objects.create(organization=self.organization, name="Speech", code="speech")
        provider = Integration.objects.create(
            organization=self.organization, kind="LLM_PROVIDER", provider="CUSTOM", secret="unit-test-never-sent",
            name="Speech", config={"base_url": "https://example.invalid/v1"}, status="OK",
        )
        AIAgent.objects.create(channel=self.channel, name="Speech", provider_integration=provider)
        self.widget = create_web_widget(self.channel)
        self.widget.integration.config = {"microphoneMode": "dictation", "maxRecordingBytes": 1000, "maxDictationSeconds": 60}
        self.widget.integration.save(update_fields=["config"])
        self.client = APIClient()

    def issue(self, consent=False):
        response = self.client.post("/api/v1/webchat/session/", {
            "widgetKey": self.widget.public_key, **({"consentVersion": "v1"} if consent else {}),
        }, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['token']}")

    def upload(self, data=b"invalid"):
        return self.client.post("/api/v1/webchat/dictation/", {"audio": SimpleUploadedFile("audio.webm", data, content_type="audio/webm"), "duration": "1"}, format="multipart")

    def test_legacy_token_does_not_prove_consent(self):
        self.issue()
        self.assertEqual(self.upload().status_code, 400)
        self.assertFalse(Conversation.objects.exists())
        self.assertFalse(Message.objects.exists())

    def test_byte_and_container_checks_do_not_send_or_create_conversation(self):
        self.issue(consent=True)
        self.assertEqual(self.upload(bytes(1001)).status_code, 400)
        self.assertEqual(self.upload().json()["code"], "format_unsupported")
        self.assertFalse(Conversation.objects.exists())
        self.assertFalse(Message.objects.exists())

    def test_plain_text_overflow_is_rejected_without_silent_truncation(self):
        self.issue(consent=True)
        response = self.client.post("/api/v1/webchat/messages/", {"text": "x" * 4001}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Message.objects.exists())
