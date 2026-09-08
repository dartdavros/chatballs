"""Ключ шифрования секретов в БД (chatballs.identity.crypto)."""

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from chatballs.identity import crypto


class FieldEncryptionKeyTests(SimpleTestCase):
    def setUp(self) -> None:
        crypto._fernet.cache_clear()
        self.addCleanup(crypto._fernet.cache_clear)

    def test_round_trip_with_the_derived_key(self) -> None:
        # Пустой ключ — установка, до которой файл секрета ещё не доехал.
        with override_settings(CHATBALLS_FIELD_ENCRYPTION_KEY=""):
            self.assertEqual(crypto.decrypt_secret(crypto.encrypt_secret("s3cret")), "s3cret")

    def test_wrong_key_is_reported_instead_of_passing_silently(self) -> None:
        # Ровно так выглядит смена ключа шифрования. Значение не вернуть, но
        # установка не должна терять секреты без единого следа в логе.
        with override_settings(CHATBALLS_FIELD_ENCRYPTION_KEY="", SECRET_KEY="первый"):
            token = crypto.encrypt_secret("s3cret")
        crypto._fernet.cache_clear()

        with override_settings(CHATBALLS_FIELD_ENCRYPTION_KEY="", SECRET_KEY="второй"):
            with self.assertLogs("chatballs.identity.crypto", level="WARNING") as logs:
                self.assertEqual(crypto.decrypt_secret(token), "")

        self.assertIn("ключ шифрования", "\n".join(logs.output))

    def test_malformed_configured_key_fails_at_startup_not_at_first_use(self) -> None:
        with override_settings(CHATBALLS_FIELD_ENCRYPTION_KEY="не-ключ-fernet"):
            with self.assertRaises(ImproperlyConfigured):
                crypto.encrypt_secret("s3cret")

    def test_explicit_key_detaches_secrets_from_the_signing_key(self) -> None:
        # Задан явно — смена SECRET_KEY больше не делает данные нечитаемыми.
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()
        with override_settings(CHATBALLS_FIELD_ENCRYPTION_KEY=key, SECRET_KEY="первый"):
            token = crypto.encrypt_secret("s3cret")
        crypto._fernet.cache_clear()
        with override_settings(CHATBALLS_FIELD_ENCRYPTION_KEY=key, SECRET_KEY="второй"):
            self.assertEqual(crypto.decrypt_secret(token), "s3cret")
