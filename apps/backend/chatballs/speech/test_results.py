import json

from django.test import SimpleTestCase

from chatballs.speech.errors import SpeechError
from chatballs.speech.providers.yandex_results import transcript


class RecognitionSegmentsTests(SimpleTestCase):
    def test_normalized_finals_replace_original_without_doubling(self):
        records = [
            {"result": {"final": {"alternatives": [{"text": "first"}]}, "audioCursors": {"finalIndex": "1"}}},
            {"result": {"final": {"alternatives": [{"text": "second"}]}, "audioCursors": {"finalIndex": "2"}}},
            {"result": {"finalRefinement": {"finalIndex": "1", "normalizedText": {"alternatives": [{"text": "First."}]}}}},
            {"result": {"finalRefinement": {"finalIndex": "2", "normalizedText": {"alternatives": [{"text": "Second."}]}}}},
        ]
        self.assertEqual(transcript("\n".join(json.dumps(record) for record in records).encode()), "First. Second.")
        self.assertEqual(transcript(b'{"result":{"partial":{"alternatives":[{"text":"ignore"}]}}}'), "")

    def test_invalid_provider_data_is_safe(self):
        with self.assertRaises(SpeechError) as error:
            transcript(b'{"error": {"message": "SECRET"}}')
        self.assertNotIn("SECRET", str(error.exception))
