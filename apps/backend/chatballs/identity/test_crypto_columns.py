"""Шифротекст должен помещаться в колонку.

``EncryptedCharField`` кладёт в базу Fernet-токен: версия, метка времени, IV,
подпись, дополнение до блока AES и base64 поверх всего. Значение в 512
символов занимает почти 2.9 КБ — в varchar(512) оно не помещалось, и длинный
пароль SMTP или ключ S3 ронял запись уже в базе.
"""

from __future__ import annotations

from django.test import TestCase

from chatballs.identity.crypto import ciphertext_length, decrypt_secret, encrypt_secret
from chatballs.identity.instance_settings import InstanceSettings
from chatballs.tenancy.storage_settings import StorageSettings


class CiphertextLengthTests(TestCase):
    def test_estimate_covers_the_real_token(self) -> None:
        for plaintext_chars in (1, 16, 255, 512, 1024):
            value = "щ" * plaintext_chars  # 2 байта на символ в UTF-8
            self.assertLessEqual(
                len(encrypt_secret(value)),
                ciphertext_length(plaintext_chars),
                f"оценка мала для {plaintext_chars} символов",
            )

    def test_round_trip_survives(self) -> None:
        value = "п" * 400
        self.assertEqual(decrypt_secret(encrypt_secret(value)), value)


class EncryptedColumnWidthTests(TestCase):
    def test_long_smtp_password_is_stored(self) -> None:
        password = "Пароль-" + "x" * 500
        row = InstanceSettings.load()
        row.email_host = "smtp.example.test"
        row.email_password = password
        row.save(update_fields=["email_host", "email_password", "updated_at"])

        row.refresh_from_db()
        self.assertEqual(row.email_password, password)

    def test_long_s3_keys_are_stored(self) -> None:
        secret = "S" * 500
        row = StorageSettings.load()
        row.s3_access_key = "A" * 500
        row.s3_secret_key = secret
        row.save(update_fields=["s3_access_key", "s3_secret_key"])

        row.refresh_from_db()
        self.assertEqual(row.s3_secret_key, secret)
