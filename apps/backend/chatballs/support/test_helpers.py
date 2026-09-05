"""Хелпер генерации Product Support Token для тестов (HS256, SPEC-HUB-0011 §4).

Вне тестов не используется: продуктовый backend выпускает токен своим секретом.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_support_token(
    *,
    secret: str,
    iss: str = "app",
    contract: str = "app.support.v1",
    data: dict[str, Any] | None = None,
    exp_delta: int = 600,
    jti: str = "test_jti_001",
    aud: str = "chatballs.support",
) -> str:
    """Подписанный HS256 Product Support Token для тестов."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "iss": iss,
        "aud": aud,
        "contract": contract,
        "iat": now,
        "exp": now + exp_delta,
        "jti": jti,
        "data": data or {},
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


# Пример payload Acme (SPEC-HUB-0011 §4.1 / §5.2).
ACME_DATA = {
    "doctor": {"id": "u_456", "name": "Иван Петров", "email": "doctor@example.com"},
    "clinic": {"id": "c_123", "name": "Клиника Альфа"},
    "subscription": {"tariff": "pro", "status": "active"},
}
