import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """Ключ шифрования секретов в БД.

    Ключ лежит в томе секретов рядом с остальными: его кладёт туда первый
    старт стека (deploy/secrets/generate-instance-secrets.sh), выводя из ключа
    подписи ровно тем же способом, что и фолбэк ниже. Значение от этого не
    меняется, зато перестаёт следовать за SECRET_KEY: до появления файла смена
    ключа подписи молча делала нечитаемым всё зашифрованное — секреты TOTP,
    токены интеграций, пароль SMTP, ключи S3.

    Фолбэк остаётся для установок, где файла ещё нет, и для тестов.
    """
    configured = getattr(settings, "CHATBALLS_FIELD_ENCRYPTION_KEY", "")
    if configured:
        try:
            return Fernet(configured.encode() if isinstance(configured, str) else configured)
        except (ValueError, TypeError) as error:
            # Иначе неверный ключ вскрылся бы не здесь, а при первой расшифровке —
            # пустым секретом вместо внятной ошибки конфигурации.
            raise ImproperlyConfigured(
                "CHATBALLS_FIELD_ENCRYPTION_KEY должен быть ключом Fernet "
                "(44 символа urlsafe-base64, Fernet.generate_key())"
            ) from error
    derived = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(derived)


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        # Значение не расшифровалось — отдаём пустое, чтобы проверка TOTP
        # безопасно провалилась, а не падала с 500. Но молчать нельзя: ровно
        # так выглядит смена ключа шифрования, и без записи в лог установка
        # теряла бы секреты TOTP и токены интеграций без единого следа.
        logger.warning(
            "Не удалось расшифровать секрет из БД — значение прочитано как пустое. "
            "Обычно это значит, что сменился ключ шифрования полей "
            "(CHATBALLS_FIELD_ENCRYPTION_KEY или выведенный из CHATBALLS_SECRET_KEY)."
        )
        return ""


def ciphertext_length(plaintext_chars: int) -> int:
    """Сколько символов занимает Fernet-токен для строки такой длины.

    В колонке лежит не значение, а шифротекст: Fernet добавляет версию,
    метку времени, IV и подпись, дополняет до блока AES и кодирует всё в
    base64. Строка в 512 символов уже не помещается в varchar(512) — запись
    падала бы на длинном пароле SMTP или ключе S3. Считаем по худшему случаю:
    4 байта на символ (UTF-8).
    """
    payload = plaintext_chars * 4
    blocks = payload // 16 + 1  # PKCS#7 всегда добавляет хотя бы один байт
    raw = 57 + 16 * blocks  # 57 = версия + timestamp + IV + HMAC
    return (raw + 2) // 3 * 4  # base64 без переносов


class EncryptedCharField(models.CharField):
    """CharField, прозрачно шифрующий значение в БД (Fernet).

    ``max_length`` описывает открытое значение — то, что вводит человек. Под
    колонку берётся длина шифротекста: иначе ограничение поля и ограничение
    столбца означают разное, и запись падает уже в базе.
    """

    def __init__(self, *args, **kwargs) -> None:
        self.plaintext_max_length = kwargs.get("max_length")
        if self.plaintext_max_length:
            kwargs["max_length"] = ciphertext_length(self.plaintext_max_length)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):  # noqa: ANN001
        if not value:
            return value
        return decrypt_secret(value)

    def get_prep_value(self, value):  # noqa: ANN001
        value = super().get_prep_value(value)
        if not value:
            return value
        return encrypt_secret(value)
