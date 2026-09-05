# Настройки хранилища инстанса: одна строка на инсталляцию (не тенантная таблица,
# без RLS). Runtime-роли читают/пишут её напрямую.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import chatballs.identity.crypto

GRANTS = """
GRANT SELECT, INSERT, UPDATE ON tenancy_storagesettings
    TO chatballs_runtime_app, chatballs_runtime_platform;
GRANT USAGE, SELECT ON SEQUENCE tenancy_storagesettings_id_seq
    TO chatballs_runtime_app, chatballs_runtime_platform;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0024_user_fk_set_null"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StorageSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("backend", models.CharField(choices=[("LOCAL", "Локальный диск"), ("S3", "S3-совместимое хранилище")], default="LOCAL", max_length=8)),
                ("s3_bucket", models.CharField(blank=True, default="", max_length=255)),
                ("s3_endpoint_url", models.URLField(blank=True, default="", max_length=512)),
                ("s3_region", models.CharField(blank=True, default="", max_length=64)),
                ("s3_access_key", chatballs.identity.crypto.EncryptedCharField(blank=True, default="", max_length=512)),
                ("s3_secret_key", chatballs.identity.crypto.EncryptedCharField(blank=True, default="", max_length=512)),
                ("s3_addressing_style", models.CharField(default="path", max_length=8)),
                ("s3_verified_at", models.DateTimeField(blank=True, null=True)),
                ("s3_last_error", models.CharField(blank=True, default="", max_length=500)),
                ("migration_status", models.CharField(choices=[("IDLE", "Не запускался"), ("RUNNING", "Идёт"), ("DONE", "Завершён"), ("FAILED", "Ошибка")], default="IDLE", max_length=8)),
                ("migration_total", models.PositiveIntegerField(default=0)),
                ("migration_done", models.PositiveIntegerField(default=0)),
                ("migration_error", models.CharField(blank=True, default="", max_length=500)),
                ("migration_started_at", models.DateTimeField(blank=True, null=True)),
                ("migration_finished_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Настройки хранилища"},
        ),
        migrations.RunSQL(GRANTS, migrations.RunSQL.noop),
    ]
