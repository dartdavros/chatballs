import base64
import json

from django.test import SimpleTestCase

from chatballs.speech.errors import SpeechError
from chatballs.speech.providers.yandex_tts import decode_segment, text_parts
from chatballs.speech.tts_contract import validate_language, validate_selection


class SynthesisContractTests(SimpleTestCase):
    def test_playback_disclosure_changes_consent_version_without_changing_authored_text(self):
        from chatballs.webchat.pre_chat import normalize_consent

        previous = {"consent_text": "Existing consent", "consent_version": "v3", "answerPlaybackEnabled": False}
        enabled = normalize_consent({"answerPlaybackEnabled": True}, previous)
        self.assertEqual(enabled, {"consent_text": "Existing consent", "consent_version": "v4"})
        self.assertEqual(normalize_consent({}, previous)["consent_version"], "v3")
        self.assertEqual(normalize_consent({"answerPlaybackEnabled": True}, {**enabled, "answerPlaybackEnabled": True})["consent_version"], "v4")
        self.assertEqual(normalize_consent({"answerPlaybackEnabled": False}, {**enabled, "answerPlaybackEnabled": True})["consent_version"], "v5")

    def test_long_unicode_text_is_partitioned_without_loss_or_reordering(self):
        for text in ("Оформленный ответ.\nЦена 123 ₽. " * 400, "abc😀я" * 3000, "x" * 10001):
            parts = list(text_parts(text))
            self.assertEqual("".join(parts), text)
            self.assertTrue(all(0 < len(part) <= 1000 for part in parts))

    def test_pcm_parts_preserve_order_and_reject_partial_or_oversized_sound(self):
        records = [json.dumps({"result": {"audioChunk": {"data": base64.b64encode(part).decode()}}})
                   for part in (b"\x01\x02", b"\x03\x04")]
        raw = "\n".join(records).encode()
        self.assertEqual(decode_segment(raw, 4), b"\x01\x02\x03\x04")
        for invalid, limit in ((raw, 2), (raw + b'\n{"error":{"message":"SECRET"}}', 100),
                               (b'{"audioChunk":{"data":"bad"}}', 100), (b"{}", 100)):
            with self.subTest(invalid=invalid), self.assertRaises(SpeechError) as error:
                decode_segment(invalid, limit)
            self.assertNotIn("SECRET", str(error.exception))

    def test_voice_language_and_model_never_fall_back(self):
        validate_selection("", "alena")
        validate_language("Здравствуйте! Спасибо за обращение. Мы поможем выбрать подходящий тариф.", "alena")
        validate_language("Your order is ready. Please collect it at the nearest store tomorrow morning.", "john")
        for model, voice in (("unknown", "alena"), ("livetts", "alena"), ("", "unknown")):
            with self.assertRaises(SpeechError):
                validate_selection(model, voice)
        for text, voice in (("Русский ответ", "john"), ("Hello", "alena"),
                            ("Bonjour", "john"),
                            ("Bonjour, je voudrais acheter un billet pour voyager demain matin.", "john")):
            with self.assertRaises(SpeechError):
                validate_language(text, voice)
