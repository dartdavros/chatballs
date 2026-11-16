"""Bounded byte validation shared by incoming references and multipart uploads."""

import hashlib
import mimetypes
from pathlib import PurePosixPath
from types import SimpleNamespace

from chatballs.conversations.attachment_policy import MAX_FILE_BYTES, validate_upload
from chatballs.conversations.transports.base import safe_filename

CHUNK = 64 * 1024
AUDIO_SUFFIXES = {".ogg", ".opus", ".mp3", ".wav", ".m4a", ".aac", ".flac", ".webm"}
ACTIVE_TYPES = {"text/html", "application/xhtml+xml", "image/svg+xml", "application/javascript"}


def metadata(stream, *, filename, mime_type, maximum=MAX_FILE_BYTES):
    name = safe_filename(filename)
    mime = (mime_type or mimetypes.guess_type(name)[0] or "application/octet-stream").split(";")[0].lower()
    suffix = PurePosixPath(name).suffix.lower()
    if (mime.startswith(("audio/", "video/")) or mime in ACTIVE_TYPES
            or suffix in AUDIO_SUFFIXES | {".html", ".htm", ".svg"}):
        raise ValueError("unsupported_content")
    hashed, size, head = hashlib.sha256(), 0, b""
    for chunk in iter(lambda: stream.read(CHUNK), b""):
        size += len(chunk)
        if size > maximum:
            raise ValueError("payload_too_large")
        head = (head + chunk)[:512]
        hashed.update(chunk)
    if validate_upload(SimpleNamespace(name=name, size=size)):
        raise ValueError("unsupported_content")
    # Origin is checked separately. Signatures also prevent relabeling common audio as .bin.
    if (head.startswith((b"OggS", b"fLaC", b"ID3", b"\x1aE\xdf\xa3"))
            or head[:4] == b"RIFF" and head[8:12] in (b"WAVE", b"AVI ")
            or head[4:8] == b"ftyp" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")
            or head.startswith(b"MZ")):
        raise ValueError("unsupported_content")
    detected = ("image/png" if head.startswith(b"\x89PNG\r\n\x1a\n") else
                "image/jpeg" if head.startswith(b"\xff\xd8\xff") else
                "image/gif" if head.startswith((b"GIF87a", b"GIF89a")) else
                "image/webp" if head[:4] == b"RIFF" and head[8:12] == b"WEBP" else
                "application/pdf" if head.startswith(b"%PDF-") else None)
    if detected and mime not in (detected, "application/octet-stream"):
        raise ValueError("unsupported_content")
    if mime.startswith("image/") and detected != mime:
        raise ValueError("unsupported_content")
    stream.seek(0)
    return {"filename": name, "mime_type": detected or mime, "size": size, "sha256": hashed.hexdigest()}
