# ADR-HUB-0023: плоские Знания с вложениями + инструкции агента из трёх частей.
# Добавляющая часть; перенос данных — 0003, снос старых моделей — 0004.

import uuid

import django.db.models.deletion
from django.db import migrations, models

import hub_platform.ai.models


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0001_initial"),
        ("identity", "0006_alter_employeeprofile_totp_secret"),
    ]

    operations = [
        migrations.CreateModel(
            name="Knowledge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.CharField(blank=True, max_length=500)),
                ("content", models.TextField(blank=True)),
                ("is_enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="knowledge_items",
                        to="identity.organization",
                    ),
                ),
            ],
            options={"ordering": ["title"], "verbose_name_plural": "knowledge"},
        ),
        migrations.CreateModel(
            name="KnowledgeAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("file", models.FileField(max_length=512, upload_to=hub_platform.ai.models.attachment_upload_path)),
                ("original_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=128)),
                ("size", models.PositiveBigIntegerField(default=0)),
                ("extracted_text", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "knowledge",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="ai.knowledge",
                    ),
                ),
            ],
            options={"ordering": ["original_name"]},
        ),
        migrations.AddConstraint(
            model_name="knowledgeattachment",
            constraint=models.UniqueConstraint(fields=("knowledge", "original_name"), name="uniq_attachment_knowledge_name"),
        ),
        migrations.AddField(
            model_name="aiagent",
            name="persona",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="aiagent",
            name="tone",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="aiagent",
            name="instructions",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="aiagent",
            name="knowledge_items",
            field=models.ManyToManyField(blank=True, related_name="agents", to="ai.knowledge"),
        ),
        # Переходное поле: фрагменты перевешиваются с версии документа на знание
        # в 0003; в 0004 поле становится обязательным, version удаляется.
        migrations.AddField(
            model_name="knowledgefragment",
            name="knowledge",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="fragments",
                to="ai.knowledge",
            ),
        ),
    ]
