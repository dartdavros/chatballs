import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    configured = getattr(settings, "CHATBALLS_FIELD_ENCRYPTION_KEY", "")
    if configured:
        return Fernet(configured.encode() if isinstance(configured, str) else configured)
    # Dev/тестовый фолбэк: детерминированный ключ из SECRET_KEY (в production задаётся отдельно).
    derived = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(derived)


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        # Повреждённое/неподходящее значение трактуем как отсутствие секрета,
        # чтобы проверка TOTP безопасно провалилась, а не падала с 500.
        return ""


class EncryptedCharField(models.CharField):
    """CharField прозрачно шифрующий значение в БД (Fernet)."""

    def from_db_value(self, value, expression, connection):  # noqa: ANN001
        if not value:
            return value
        return decrypt_secret(value)

    def get_prep_value(self, value):  # noqa: ANN001
        value = super().get_prep_value(value)
        if not value:
            return value
        return encrypt_secret(value)
