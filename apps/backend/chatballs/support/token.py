"""Проверка Product Support Token (SPEC-HUB-0011 §4).

HS256 JWT через stdlib (hmac/hashlib/base64) — без внешних зависимостей.
Целевой вариант RS256/EdDSA с JWKS — TODO (SPEC §4.3).

Token envelope claims: iss, aud, contract, iat, exp, jti, data.
Подпись проверяется по per-product secret (Product.support_token_secret, Fernet).
Возвращает разобранные claims; raw token не сохраняется и не логируется.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import UTC
from typing import Any

from chatballs.support import errors

SUPPORT_AUDIENCE = "edevshub.support"


@dataclass(frozen=True)
class TokenClaims:
    iss: str
    aud: str
    contract: str
    iat: int
    exp: int
    jti: str
    data: dict[str, Any]

    @property
    def jti_hash(self) -> str:
        return hashlib.sha256(self.jti.encode("utf-8")).hexdigest()


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def verify_support_token(*, token: str, secret: str) -> TokenClaims:
    """Проверяет подпись и envelope claims. Поднимает SupportSessionError при ошибке.

    Не проверяет product/contract/channel binding — это делает сервис по claims.
    """
    if not token:
        raise errors.SupportSessionError(errors.TOKEN_MISSING)
    parts = token.split(".")
    if len(parts) != 3:
        raise errors.SupportSessionError(errors.TOKEN_SIGNATURE_INVALID)
    header_b64, payload_b64, signature_b64 = parts

    try:
        header = json.loads(_b64url_decode(header_b64))
    except (ValueError, json.JSONDecodeError):
        raise errors.SupportSessionError(errors.TOKEN_SIGNATURE_INVALID) from None
    if header.get("alg") != "HS256":
        raise errors.SupportSessionError(errors.TOKEN_SIGNATURE_INVALID)

    if not secret:
        raise errors.SupportSessionError(errors.TOKEN_SIGNATURE_INVALID)

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    given = _b64url_decode(signature_b64)
    if not hmac.compare_digest(expected, given):
        raise errors.SupportSessionError(errors.TOKEN_SIGNATURE_INVALID)

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        raise errors.SupportSessionError(errors.TOKEN_SIGNATURE_INVALID) from None

    return _claims_from_payload(payload)


def _claims_from_payload(payload: dict[str, Any]) -> TokenClaims:
    if not isinstance(payload, dict):
        raise errors.SupportSessionError(errors.TOKEN_SIGNATURE_INVALID)

    iss = payload.get("iss")
    aud = payload.get("aud")
    contract = payload.get("contract")
    iat = payload.get("iat")
    exp = payload.get("exp")
    jti = payload.get("jti")
    data = payload.get("data")

    if not isinstance(iss, str) or not iss:
        raise errors.SupportSessionError(errors.TOKEN_ISSUER_INVALID)
    if aud != SUPPORT_AUDIENCE:
        raise errors.SupportSessionError(errors.TOKEN_AUDIENCE_INVALID)
    if not isinstance(contract, str) or not contract:
        raise errors.SupportSessionError(errors.CONTRACT_NOT_FOUND)
    if not isinstance(jti, str) or not jti:
        raise errors.SupportSessionError(errors.TOKEN_SIGNATURE_INVALID)
    if not isinstance(iat, int) or not isinstance(exp, int):
        raise errors.SupportSessionError(errors.TOKEN_EXPIRED)

    now = int(time.time())
    if exp < now:
        raise errors.SupportSessionError(errors.TOKEN_EXPIRED)

    if not isinstance(data, dict):
        raise errors.SupportSessionError(errors.PAYLOAD_SCHEMA_INVALID)

    return TokenClaims(
        iss=iss, aud=aud, contract=contract, iat=iat, exp=exp, jti=jti, data=data
    )


def claims_datetimes(claims: TokenClaims):
    """iat/exp как aware datetime (для snapshot token_issued_at/expires_at)."""
    from datetime import datetime

    return (
        datetime.fromtimestamp(claims.iat, tz=UTC),
        datetime.fromtimestamp(claims.exp, tz=UTC),
    )
