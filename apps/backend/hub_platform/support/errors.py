"""Машинные коды ошибок support-сессии (SPEC-HUB-0011 §14).

Публичный ответ widget всегда безопасный: {"error":"support_unavailable","message":...}.
Внутренний machine code пишется в audit payload и не раскрывается пользователю.
"""

from __future__ import annotations

# Публичное сообщение для всех категорий отказа — без технических деталей.
PUBLIC_SUPPORT_UNAVAILABLE = (
    "Поддержка временно недоступна. Обновите страницу или обратитесь позже."
)


# Внутренние machine codes для audit/debug.
TOKEN_MISSING = "TOKEN_MISSING"
TOKEN_SIGNATURE_INVALID = "TOKEN_SIGNATURE_INVALID"
TOKEN_EXPIRED = "TOKEN_EXPIRED"
TOKEN_AUDIENCE_INVALID = "TOKEN_AUDIENCE_INVALID"
TOKEN_ISSUER_INVALID = "TOKEN_ISSUER_INVALID"
CONTRACT_NOT_FOUND = "CONTRACT_NOT_FOUND"
CONTRACT_DISABLED = "CONTRACT_DISABLED"
CONTRACT_CHANNEL_NOT_ALLOWED = "CONTRACT_CHANNEL_NOT_ALLOWED"
PAYLOAD_SCHEMA_INVALID = "PAYLOAD_SCHEMA_INVALID"
SUBJECT_MAPPING_EMPTY = "SUBJECT_MAPPING_EMPTY"
CHANNEL_NOT_SUPPORT = "CHANNEL_NOT_SUPPORT"
CHANNEL_PRODUCT_MISMATCH = "CHANNEL_PRODUCT_MISMATCH"
ANONYMOUS_NOT_ALLOWED = "ANONYMOUS_NOT_ALLOWED"


class SupportSessionError(Exception):
    """Отказ старта support-сессии с машинным кодом причины.

    code — внутренний machine code (для audit); пользователю отдаётся только
    безопасное публичное сообщение без раскрытия деталей проверки.
    """

    def __init__(self, code: str, message: str = PUBLIC_SUPPORT_UNAVAILABLE) -> None:
        super().__init__(message)
        self.code = code
