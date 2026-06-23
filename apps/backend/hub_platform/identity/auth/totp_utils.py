import base64
import hashlib
import hmac
import os
import struct
import time

from hub_platform.identity.models import HumanUser

TOTP_SESSION_KEY = "identity_pending_totp_user_id"
TOTP_ISSUER = "Edevs Hub"
TOTP_PERIOD_SECONDS = 30


def _generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")


def _decode_totp_secret(secret: str) -> bytes:
    normalized = secret.strip().replace(" ", "").upper()
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    return base64.b32decode(normalized + padding)


def _totp_code(secret: str, for_time: int | None = None) -> str:
    timestamp = int(time.time() if for_time is None else for_time)
    counter = timestamp // TOTP_PERIOD_SECONDS
    digest = hmac.new(_decode_totp_secret(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1_000_000:06d}"


def _verify_totp(secret: str, code: str) -> bool:
    normalized = "".join(character for character in code if character.isdigit())
    if len(normalized) != 6:
        return False
    now = int(time.time())
    return any(
        hmac.compare_digest(_totp_code(secret, now + (offset * TOTP_PERIOD_SECONDS)), normalized)
        for offset in (-1, 0, 1)
    )


def _ensure_totp_secret(user: HumanUser) -> str:
    profile = user.employee_profile
    if not profile.totp_secret:
        profile.totp_secret = _generate_totp_secret()
        profile.save(update_fields=["totp_secret"])
    return profile.totp_secret
