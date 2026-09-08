import base64
import hashlib
import hmac
import os
import struct
import time

from chatballs.identity.models import HumanUser

TOTP_SESSION_KEY = "identity_pending_totp_user_id"
# Когда пароль приняли и остался только код. Без отметки времени начатая и
# брошенная попытка входа висела бы в сессии сколько угодно долго: чужая
# вкладка через неделю дописывала бы код и получала вход.
TOTP_STARTED_KEY = "identity_pending_totp_started_at"
TOTP_CHALLENGE_TTL_SECONDS = 5 * 60
TOTP_ISSUER = "Chatballs"
TOTP_PERIOD_SECONDS = 30
# Допуск на расхождение часов с телефоном: интервал до и после текущего.
TOTP_WINDOW = (-1, 0, 1)


def _generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")


def _decode_totp_secret(secret: str) -> bytes:
    normalized = secret.strip().replace(" ", "").upper()
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    return base64.b32decode(normalized + padding)


def current_counter(now: int | None = None) -> int:
    return int(time.time() if now is None else now) // TOTP_PERIOD_SECONDS


def _totp_code(secret: str, for_time: int | None = None) -> str:
    return _code_for_counter(secret, current_counter(for_time))


def _code_for_counter(secret: str, counter: int) -> str:
    digest = hmac.new(
        _decode_totp_secret(secret), struct.pack(">Q", counter), hashlib.sha1
    ).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1_000_000:06d}"


def verify_totp(secret: str, code: str, *, after_counter: int = 0) -> int | None:
    """Номер интервала принятого кода или None.

    ``after_counter`` — последний уже использованный интервал этого
    пользователя: коды до него включительно не принимаются повторно
    (RFC 6238 §5.2). Возвращённый номер вызывающий обязан сохранить, иначе
    защиты от повтора нет.
    """
    normalized = "".join(character for character in code if character.isdigit())
    if len(normalized) != 6 or not secret:
        return None
    now = current_counter()
    for offset in TOTP_WINDOW:
        counter = now + offset
        if counter <= after_counter:
            continue
        if hmac.compare_digest(_code_for_counter(secret, counter), normalized):
            return counter
    return None


def accept_totp_code(user: HumanUser, code: str) -> bool:
    """Принять код и запомнить его интервал, чтобы он не сработал второй раз."""
    from django.utils import timezone

    counter = verify_totp(user.totp_secret, code, after_counter=user.totp_last_counter)
    if counter is None:
        return False
    user.totp_last_counter = counter
    user.totp_last_used_at = timezone.now()
    user.save(update_fields=["totp_last_counter", "totp_last_used_at"])
    return True


def _ensure_totp_secret(user: HumanUser) -> str:
    if not user.totp_secret:
        user.totp_secret = _generate_totp_secret()
        user.save(update_fields=["totp_secret"])
    return user.totp_secret
