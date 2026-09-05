"""Stateless widget-credential для polling/send support-диалога виджетом.

После старта support-сессии (verify Product Support Token) виджету выдаётся
короткоживущий stateless-credential: виджет ходит с ним на poll/send endpoints,
не пере-верифицируя Product Support Token каждый запрос. Credential — HMAC-signed
JSON {conversation_id, snapshot_id, exp}, подписан SECRET_KEY. Без БД (нет отзыва —
компромисс для виджета; credential короткоживущий и привязан к conversation/snapshot).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import TypedDict

from django.conf import settings

# Срок жизни credential длиннее Product Support Token (виджет работает долго),
# но ограничен — пере-выпуск через re-start сессии при истечении.
WIDGET_CREDENTIAL_TTL_SECONDS = 60 * 60  # 1 час


class WidgetClaims(TypedDict):
    conversation_id: int
    snapshot_id: int
    exp: int


def _secret() -> bytes:
    return (settings.SECRET_KEY or "").encode("utf-8")


def _sign(payload_b64: str) -> str:
    return base64.urlsafe_b64encode(
        hmac.new(_secret(), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    ).rstrip(b"=").decode()


def issue_widget_credential(*, conversation_id: int, snapshot_id: int) -> str:
    payload: WidgetClaims = {
        "conversation_id": conversation_id,
        "snapshot_id": snapshot_id,
        "exp": int(time.time()) + WIDGET_CREDENTIAL_TTL_SECONDS,
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    return f"{payload_b64}.{_sign(payload_b64)}"


def verify_widget_credential(credential: str) -> WidgetClaims | None:
    if not credential or "." not in credential:
        return None
    payload_b64, signature = credential.rsplit(".", 1)
    expected = _sign(payload_b64)
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        padding = "=" * (-len(payload_b64) % 4)
        raw = base64.urlsafe_b64decode(payload_b64 + padding)
        claims = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(claims, dict):
        return None
    exp = claims.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        return None
    conversation_id = claims.get("conversation_id")
    snapshot_id = claims.get("snapshot_id")
    if not isinstance(conversation_id, int) or not isinstance(snapshot_id, int):
        return None
    return {"conversation_id": conversation_id, "snapshot_id": snapshot_id, "exp": exp}
