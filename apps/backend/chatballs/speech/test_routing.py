from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from chatballs.speech.contracts import capabilities
from chatballs.speech.errors import SpeechError
from chatballs.speech.routing import resolve_model, selected_integration
from chatballs.webchat.recording_configuration import normalize_recording


class SpeechRoutingTests(SimpleTestCase):
    def integration(self, provider="CUSTOM", **changes):
        return SimpleNamespace(provider=provider, organization_id=1, is_active=True, status="OK", secret="unit-test", config=changes.pop("config", {}), **changes)

    def channel(self, explicit=None, inherited=None, model=""):
        agent = SimpleNamespace(transcription_integration=explicit, provider_integration=inherited, transcription_model=model)
        return SimpleNamespace(organization_id=1, ai_agent=agent)

    def test_empty_selection_inherits_compatible_stt_and_uses_provider_defaults(self):
        previous = self.integration()
        channel = self.channel(inherited=previous)
        self.assertIs(selected_integration(channel), previous)
        self.assertEqual(resolve_model(channel), "whisper-1")
        yandex = self.integration("YANDEX_SPEECHKIT")
        channel = self.channel(explicit=yandex, inherited=previous)
        self.assertEqual(resolve_model(channel), "general")
        yandex.config["transcription_model"] = "general:rc"
        self.assertEqual(resolve_model(channel), "general:rc")
        channel.ai_agent.transcription_model = "general"
        self.assertEqual(resolve_model(channel), "general")
        channel.ai_agent.transcription_model = "whisper-1"
        with self.assertRaises(SpeechError):
            resolve_model(channel)

    def test_explicit_broken_selection_never_falls_back(self):
        for changes in ({"secret": ""}, {"is_active": False}, {"status": "ERROR"}, {"organization_id": 2}):
            integration = self.integration("YANDEX_SPEECHKIT")
            for key, value in changes.items():
                setattr(integration, key, value)
            with self.subTest(changes=changes), self.assertRaises(SpeechError):
                selected_integration(self.channel(explicit=integration, inherited=self.integration()))
        self.assertFalse(capabilities("DEMO").stt)
        with self.assertRaises(SpeechError):
            selected_integration(self.channel(inherited=self.integration("DEMO")))

    def test_recording_limits_are_positive_strict_integers_and_keep_previous_mode(self):
        previous = {"microphoneMode": "off", "maxRecordingBytes": 1234, "maxDictationSeconds": 12}
        self.assertEqual(normalize_recording({}, previous), {**previous, "answerPlaybackEnabled": False})
        for key, value in (("maxRecordingBytes", 0), ("maxRecordingBytes", True), ("maxRecordingBytes", 10485761), ("maxDictationSeconds", "60"), ("maxDictationSeconds", 61), ("microphoneMode", [])):
            with self.subTest(key=key, value=value), self.assertRaises(ValidationError):
                normalize_recording({key: value}, {})
