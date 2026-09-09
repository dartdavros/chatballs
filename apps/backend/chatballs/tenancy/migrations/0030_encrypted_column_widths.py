"""Ключи S3: колонки под шифротекст (см. identity.0034)."""

from django.db import migrations

import chatballs.identity.crypto


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0029_drop_product_support"),
    ]

    operations = [
        migrations.AlterField(
            model_name="storagesettings",
            name="s3_access_key",
            field=chatballs.identity.crypto.EncryptedCharField(
                blank=True, default="", max_length=2828
            ),
        ),
        migrations.AlterField(
            model_name="storagesettings",
            name="s3_secret_key",
            field=chatballs.identity.crypto.EncryptedCharField(
                blank=True, default="", max_length=2828
            ),
        ),
    ]
