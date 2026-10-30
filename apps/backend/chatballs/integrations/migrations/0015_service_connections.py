"""Сервисные подключения (SPEC-0037 R-1): вид SERVICE, общий provider ADAPTER,
настройки адаптера, одноразовый OAuth state и операционные файлы.

Старые подключения, их секреты и разрешения не трогаются; сценарии и новые
права миграция не включает (R-29).
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import chatballs.identity.crypto
import chatballs.integrations.scenario_state.files


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0048_organization_operation_mode"),
        ("integrations", "0014_merge_field_access_and_tools"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="integration",
            name="kind",
            field=models.CharField(
                choices=[
                    ("LLM_PROVIDER", "LLM-провайдер"),
                    ("MESSENGER", "Подключение-мессенджер"),
                    ("EXTERNAL_SERVER", "Внешний сервер"),
                    ("SERVICE", "Сервис"),
                ],
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="integration",
            name="provider",
            field=models.CharField(
                choices=[
                    ("OPENROUTER", "OpenRouter"),
                    ("CUSTOM", "Custom (OpenAI-compatible)"),
                    ("DEMO", "Демо-провайдер (без ключа)"),
                    ("MAX", "MAX"),
                    ("TELEGRAM", "Telegram"),
                    ("VK", "ВКонтакте"),
                    ("WEB", "Web-виджет"),
                    ("EMAIL", "Email (IMAP/SMTP)"),
                    ("MCP", "MCP-сервер"),
                    ("HTTP", "HTTP-запрос"),
                    ("ADAPTER", "Адаптер сервиса"),
                ],
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="ServiceConnectionSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("adapter_key", models.CharField(max_length=64)),
                ("adapter_version", models.PositiveIntegerField()),
                ("auth_method", models.CharField(max_length=64)),
                ("settings", models.JSONField(blank=True, default=dict)),
                ("credentials", chatballs.identity.crypto.EncryptedCharField(blank=True, max_length=174860)),
                ("credentials_expires_at", models.DateTimeField(blank=True, null=True)),
                ("refresh_claim", models.UUIDField(blank=True, null=True)),
                ("refresh_claim_until", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "integration",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_settings",
                        to="integrations.integration",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="+", to="identity.organization"
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="ServiceOAuthState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("state_hash", models.CharField(max_length=64, unique=True)),
                ("adapter_key", models.CharField(max_length=64)),
                ("adapter_version", models.PositiveIntegerField()),
                ("auth_method", models.CharField(max_length=64)),
                ("draft", models.JSONField(blank=True, default=dict)),
                ("code_verifier", chatballs.identity.crypto.EncryptedCharField(blank=True, max_length=780)),
                ("redirect_uri", models.CharField(max_length=512)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Ожидает разрешения"),
                            ("COMPLETED", "Подключено"),
                            ("DENIED", "Доступ не предоставлен"),
                            ("FAILED", "Ошибка"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                ("error_code", models.CharField(blank=True, max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "integration",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="integrations.integration",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="+", to="identity.organization"
                    ),
                ),
                (
                    "result",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="integrations.integration",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="+", to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="ServiceFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "file",
                    models.FileField(
                        max_length=512,
                        upload_to=chatballs.integrations.scenario_state.files.service_file_upload_path,
                    ),
                ),
                ("name", models.CharField(blank=True, max_length=255)),
                ("content_type", models.CharField(max_length=128)),
                ("size", models.PositiveBigIntegerField(default=0)),
                ("sha256", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "integration",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_files",
                        to="integrations.integration",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="+", to="identity.organization"
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]
