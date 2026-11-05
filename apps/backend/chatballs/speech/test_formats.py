import subprocess

from django.test import SimpleTestCase

from chatballs.speech.errors import SpeechError
from chatballs.speech.formats import BYTES_PER_SECOND, normalize_audio, recording_duration


def encode(seconds: float, container: str) -> bytes:
    """Настоящий FFmpeg кодирует PCM-сигнал в памяти, внешнего STT здесь нет."""
    codec = "aac" if container == "mp4" else "libopus"
    options = ["-movflags", "frag_keyframe+empty_moov"] if container == "mp4" else []
    return subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-f", "s16le", "-ar", "16000", "-ac", "1", "-i", "pipe:0",
         "-c:a", codec, *options, "-f", container, "pipe:1"],
        input=bytes(round(seconds * BYTES_PER_SECOND)), capture_output=True, timeout=10, check=True,
    ).stdout


class RealAudioDecodingTests(SimpleTestCase):
    def test_browser_containers_decode_and_actual_duration_is_measured(self):
        for container, content_type in (("webm", "audio/webm"), ("ogg", "audio/ogg"), ("mp4", "audio/mp4")):
            with self.subTest(container=container):
                data = encode(1, container)
                result = normalize_audio(data)
                self.assertEqual(result.content_type, content_type)
                self.assertAlmostEqual(result.seconds, 1, delta=.15)
                actual_type, duration = recording_duration(data, max_bytes=10485760)
                self.assertEqual(actual_type, content_type)
                self.assertAlmostEqual(duration, 1, delta=.15)

    def test_sixty_seconds_are_accepted_and_decoded_overflow_is_rejected(self):
        exact = normalize_audio(encode(60, "webm"))
        self.assertAlmostEqual(exact.seconds, 60, delta=.01)
        with self.assertRaises(SpeechError) as raised:
            normalize_audio(encode(61, "ogg"))
        self.assertEqual(raised.exception.code, "too_long")

    def test_invalid_container_and_byte_limit_fail_before_decoding(self):
        for audio, code in ((b"not audio", "format_unsupported"), (bytes(11), "too_large")):
            with self.subTest(code=code), self.assertRaises(SpeechError) as raised:
                normalize_audio(audio, max_bytes=10 if code == "too_large" else 100)
            self.assertEqual(raised.exception.code, code)
