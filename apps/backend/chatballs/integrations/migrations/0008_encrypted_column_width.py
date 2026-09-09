"""Секрет интеграции: колонка под шифротекст (см. identity.0034)."""

from django.db import migrations

import chatballs.identity.crypto


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0007_integration_feature_flags"),
    ]

    operations = [
        migrations.AlterField(
            model_name="integration",
            name="secret",
            field=chatballs.identity.crypto.EncryptedCharField(blank=True, max_length=5560),
        ),
    ]
