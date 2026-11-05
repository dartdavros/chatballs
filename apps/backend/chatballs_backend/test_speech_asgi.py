from io import BytesIO

from django.core.exceptions import RequestAborted
from django.test import SimpleTestCase

from chatballs_backend.speech_asgi import MAX_DICTATION_BODY, DictationASGIHandler


class DictationBodyTests(SimpleTestCase):
    async def test_body_larger_than_default_upload_spool_stays_in_memory(self):
        handler = DictationASGIHandler()
        async def receive():
            return {"type": "http.request", "body": bytes(3 * 1024 * 1024), "more_body": False}
        body = await handler.read_body(receive)
        try:
            self.assertIsInstance(body, BytesIO)
            self.assertEqual(len(body.getbuffer()), 3 * 1024 * 1024)
        finally:
            body.close()

    async def test_oversized_chunk_is_aborted_without_spooling(self):
        handler = DictationASGIHandler()
        async def receive():
            return {"type": "http.request", "body": bytes(MAX_DICTATION_BODY + 1), "more_body": False}
        with self.assertRaises(RequestAborted):
            await handler.read_body(receive)
