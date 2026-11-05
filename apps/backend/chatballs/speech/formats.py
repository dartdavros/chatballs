"""Ограниченные FFmpeg pipes: входной MIME и duration не являются доказательством."""

import io
import json
import subprocess
import wave
from dataclasses import dataclass

from chatballs.speech.contracts import MAX_RECORDING_BYTES
from chatballs.speech.errors import SpeechError

SAMPLE_RATE = 16000
BYTES_PER_SECOND = SAMPLE_RATE * 2


@dataclass(frozen=True, slots=True)
class NormalizedAudio:
    pcm: bytes
    content_type: str

    @property
    def seconds(self) -> float:
        return len(self.pcm) / BYTES_PER_SECOND

    def wav(self) -> bytes:
        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(SAMPLE_RATE)
                output.writeframes(self.pcm)
            return buffer.getvalue()


def _container(data: bytes) -> tuple[str, str, set[str]]:
    if data.startswith(b"OggS"):
        return "ogg", "audio/ogg", {"opus"}
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "matroska", "audio/webm", {"opus"}
    if data[4:8] == b"ftyp":
        return "mov", "audio/mp4", {"aac", "alac", "opus"}
    if data.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return "wav", "audio/wav", {"pcm_s16le"}
    raise SpeechError("format_unsupported")


def _probe(data: bytes, max_bytes: int):
    if not data:
        raise SpeechError("empty")
    if len(data) > max_bytes:
        raise SpeechError("too_large")
    demuxer, content_type, codecs = _container(data)
    source = ["-protocol_whitelist", "pipe", "-probesize", "1048576", "-analyzeduration", "2000000", "-f", demuxer, "-i", "pipe:0"]
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", *source, "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "json"],
            input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5, check=False,
        )
        streams = json.loads(probe.stdout).get("streams", [])
        if probe.returncode or len(streams) != 1 or streams[0].get("codec_name") not in codecs:
            raise SpeechError("format_unsupported")
    except FileNotFoundError:
        raise SpeechError("decoder_unavailable") from None
    except subprocess.TimeoutExpired:
        raise SpeechError("timeout") from None
    except (ValueError, TypeError):
        raise SpeechError("format_unsupported") from None
    return source, content_type


def normalize_audio(data: bytes, *, max_bytes: int = MAX_RECORDING_BYTES, max_seconds: int = 60) -> NormalizedAudio:
    source, content_type = _probe(data, max_bytes)
    try:
        # -t caps decoded output even for a tiny compressed multi-hour input.
        # One extra second distinguishes the exact limit from over-limit audio.
        decoded = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-threads", "1", *source,
             "-map", "0:a:0", "-vn", "-sn", "-dn", "-t", str(max_seconds + 1),
             "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", "-f", "s16le", "pipe:1"],
            input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, check=False,
        )
    except FileNotFoundError:
        raise SpeechError("decoder_unavailable") from None
    except subprocess.TimeoutExpired:
        raise SpeechError("timeout") from None
    except (ValueError, TypeError):
        raise SpeechError("format_unsupported") from None
    if decoded.returncode or not decoded.stdout:
        raise SpeechError("format_unsupported")
    if len(decoded.stdout) > max_seconds * BYTES_PER_SECOND:
        raise SpeechError("too_long")
    return NormalizedAudio(decoded.stdout, content_type)


def recording_duration(data: bytes, *, max_bytes: int) -> tuple[str, float]:
    """Отправленное голосовое: декодируем в null sink без нового лимита времени записи."""
    source, content_type = _probe(data, max_bytes)
    try:
        result = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-threads", "1", *source,
             "-map", "0:a:0", "-vn", "-sn", "-dn", "-ac", "1", "-ar", str(SAMPLE_RATE),
             "-progress", "pipe:1", "-nostats", "-f", "null", "-"],
            input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, check=False,
        )
        times = [int(line.split(b"=", 1)[1]) for line in result.stdout.splitlines() if line.startswith(b"out_time_us=")]
        if result.returncode or not times or times[-1] <= 0:
            raise SpeechError("format_unsupported")
        return content_type, times[-1] / 1_000_000
    except FileNotFoundError:
        raise SpeechError("decoder_unavailable") from None
    except subprocess.TimeoutExpired:
        raise SpeechError("timeout") from None
    except ValueError:
        raise SpeechError("format_unsupported") from None
