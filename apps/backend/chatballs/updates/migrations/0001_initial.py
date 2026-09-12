import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UpdateState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("latest_version", models.CharField(blank=True, default="", max_length=32)),
                ("latest_name", models.CharField(blank=True, default="", max_length=128)),
                ("latest_notes", models.TextField(blank=True, default="")),
                ("latest_published_at", models.DateTimeField(blank=True, null=True)),
                ("latest_compose_url", models.URLField(blank=True, default="", max_length=512)),
                ("latest_page_url", models.URLField(blank=True, default="", max_length=512)),
                ("checked_at", models.DateTimeField(blank=True, null=True)),
                ("check_error", models.CharField(blank=True, default="", max_length=500)),
                ("install_version", models.CharField(blank=True, default="", max_length=32)),
                (
                    "install_status",
                    models.CharField(
                        choices=[
                            ("IDLE", "Не запускалась"),
                            ("REQUESTED", "Запрошена"),
                            ("RUNNING", "Идёт"),
                            ("DONE", "Завершена"),
                            ("FAILED", "Ошибка"),
                        ],
                        default="IDLE",
                        max_length=12,
                    ),
                ),
                ("install_message", models.CharField(blank=True, default="", max_length=1000)),
                ("install_requested_at", models.DateTimeField(blank=True, null=True)),
                ("install_updated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "install_requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name": "Обновления установки"},
        ),
    ]
