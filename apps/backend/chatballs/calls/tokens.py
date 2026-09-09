from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import dataclass

from django.conf import settings

from chatballs.calls.errors import CallTokenError
from chatballs.calls.models import ParticipantSide

ACCESS_TOKEN_VERSION = 1
ACCESS_TOKEN_PURPOSE = "call-access"


@dataclass(frozen=True)
class CallAccessClaims:
    call_session_id: uuid.UUID
    side: str
    subject_id: str
    issued_at: int
    expires_at: int
    token_id: str


def _derived_secret(purpose: str) -> bytes:
    return hmac.new(
        (settings.SECRET_KEY or "").encode("utf-8"),
        f"hub:{purpose}:v1".encode(),
        hashlib.sha256,
    ).digest()


def hash_invite_token(token: str) -> str:
    return hmac.new(_derived_secret("call-invite"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_invite_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hash_invite_token(token)


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _sign(payload: str) -> str:
    digest = hmac.new(
        _derived_secret(ACCESS_TOKEN_PURPOSE),
        payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def issue_call_access_token(*, call_session_id: uuid.UUID, side: str, subject_id: str) -> str:
    if side not in ParticipantSide.values:
        raise ValueError("Unknown participant side")
    now = int(time.time())
    payload = {
        "v": ACCESS_TOKEN_VERSION,
        "purpose": ACCESS_TOKEN_PURPOSE,
        "call_session_id": str(call_session_id),
        "side": side,
        "subject_id": str(subject_id),
        "iat": now,
        "exp": now + settings.CHATBALLS_CALL_ACCESS_TTL_SECONDS,
        "jti": secrets.token_urlsafe(16),
    }
    encoded = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    return f"{encoded}.{_sign(encoded)}"


def verify_call_access_token(token: str) -> CallAccessClaims:
    message = "Недействительный или истёкший call access token"
    if not token or "." not in token:
        raise CallTokenError(message)
    encoded, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(_sign(encoded), signature):
        raise CallTokenError(message)
    try:
        payload = json.loads(_b64decode(encoded))
        call_session_id = uuid.UUID(str(payload["call_session_id"]))
    except (binascii.Error, UnicodeDecodeError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise CallTokenError(message) from None

    now = int(time.time())
    if (
        payload.get("v") != ACCESS_TOKEN_VERSION
        or payload.get("purpose") != ACCESS_TOKEN_PURPOSE
        or payload.get("side") not in ParticipantSide.values
        or not isinstance(payload.get("subject_id"), str)
        or not isinstance(payload.get("iat"), int)
        or not isinstance(payload.get("exp"), int)
        or not isinstance(payload.get("jti"), str)
        or payload["iat"] > now + 30
        or payload["exp"] <= now
    ):
        raise CallTokenError(message)

    return CallAccessClaims(
        call_session_id=call_session_id,
        side=payload["side"],
        subject_id=payload["subject_id"],
        issued_at=payload["iat"],
        expires_at=payload["exp"],
        token_id=payload["jti"],
    )
