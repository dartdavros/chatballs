"""Колонка вмещает шифротекст, а не открытое значение.

``EncryptedCharField`` хранит Fernet-токен: версия, метка времени, IV, подпись,
дополнение до блока AES и base64 поверх всего. Значение в 512 символов
занимает почти 2.9 КБ, и в ``varchar(512)`` не помещалось — длинный пароль
SMTP или ключ S3 ронял запись уже в базе. ``max_length`` поля по-прежнему
описывает открытое значение; ширину столбца считает
``chatballs.identity.crypto.ciphertext_length``.
"""

from django.db import migrations

import chatballs.identity.crypto


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0033_instance_previous_public_host"),
    ]

    operations = [
        migrations.AlterField(
            model_name="humanuser",
            name="totp_secret",
            field=chatballs.identity.crypto.EncryptedCharField(blank=True, max_length=1444),
        ),
        migrations.AlterField(
            model_name="instancesettings",
            name="email_password",
            field=chatballs.identity.crypto.EncryptedCharField(
                blank=True, default="", max_length=2828
            ),
        ),
    ]
