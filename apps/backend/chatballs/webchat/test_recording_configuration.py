from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.test import TestCase

from chatballs.channels.models import Channel
from chatballs.identity.models import Organization
from chatballs.webchat.recording_configuration import public_recording
from chatballs.webchat.testing import create_web_widget


class WebRecordingMigrationTests(TestCase):
    def test_migration_preserves_voice_permissions_and_existing_configuration(self):
        organization = Organization.objects.create(name="Recording", slug="recording")
        channel = Channel.objects.create(organization=organization, name="Recording", code="recording")
        for allowed, mode in ((True, "voice_message"), (False, "off")):
            integration = create_web_widget(channel, name=f"Recording {mode}").integration
            integration.voice_messages_enabled = allowed
            integration.config = {"consent_text": "existing", "fields": [{"key": "order", "type": "string"}]}
            integration.save(update_fields=["voice_messages_enabled", "config"])
            migrate = import_module("chatballs.webchat.migrations.0010_web_recording_settings")
            migrate.preserve_web_permissions(apps, SimpleNamespace(connection=SimpleNamespace(alias="default")))
            integration.refresh_from_db()
            self.assertEqual(integration.voice_messages_enabled, allowed)
            self.assertEqual(integration.config["microphoneMode"], mode)
            self.assertEqual(integration.config["consent_text"], "existing")
            self.assertEqual(integration.config["maxRecordingBytes"], 10485760)
            self.assertEqual(integration.config["maxDictationSeconds"], 60)
            integration.config["microphoneMode"] = "dictation"
            integration.save(update_fields=["config"])
            self.assertFalse(public_recording(integration)["available"])

    def test_speechkit_is_encrypted_and_cannot_be_an_answer_provider(self):
        from django.core.exceptions import ValidationError
        from django.db import connection

        from chatballs.ai.provider_selection import (
            configure_agent_provider,
            configure_agent_transcription,
        )
        from chatballs.integrations.services import IntegrationInput, create_integration
        from chatballs.testing import system_tenant_context

        organization = Organization.objects.create(name="Speech", slug="speech-config")
        context = system_tenant_context(organization)
        integration = create_integration(context=context, data=IntegrationInput(
            provider="YANDEX_SPEECHKIT", name="Speech", secret="unit-test-never-sent", config={"folderId": "unit-folder"},
        ))
        self.assertEqual(integration.kind, "SPEECH_PROVIDER")
        self.assertEqual(configure_agent_transcription(context=context, integration_id=integration.id), integration)
        with self.assertRaises(ValidationError):
            configure_agent_provider(context=context, integration_id=integration.id)
        with connection.cursor() as cursor:
            cursor.execute("SELECT secret FROM integrations_integration WHERE id = %s", [integration.id])
            stored = cursor.fetchone()[0]
        self.assertNotEqual(stored, integration.secret)
        self.assertEqual(integration.secret, "unit-test-never-sent")
