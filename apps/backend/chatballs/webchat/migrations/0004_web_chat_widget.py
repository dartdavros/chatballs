import uuid

import django.db.models.deletion
from django.db import migrations, models

import chatballs.webchat.models


def backfill_widgets(apps, schema_editor):
    Integration = apps.get_model("integrations", "Integration")
    Channel = apps.get_model("channels", "Channel")
    WebChatWidget = apps.get_model("webchat", "WebChatWidget")
    WebSession = apps.get_model("webchat", "WebSession")

    channels = {item.id: item for item in Channel.objects.all()}
    for integration in Integration.objects.filter(provider="WEB").order_by("id"):
        channel = channels.get(integration.channel_id)
        authenticated = bool(
            channel
            and channel.requires_authenticated_product_identity
            and not channel.allow_anonymous_sessions
        )
        config = integration.config if isinstance(integration.config, dict) else {}
        presentation = {
            key: config[key]
            for key in ("title", "accent", "greeting", "quick_replies", "fallback")
            if key in config
        }
        widget = WebChatWidget.objects.create(
            organization_id=integration.organization_id,
            integration_id=integration.id,
            code=f"web-{integration.id}",
            public_key=f"wgt_{uuid.uuid4().hex}",
            name=integration.name,
            mode="AUTHENTICATED_PRODUCT" if authenticated else "ANONYMOUS",
            status=(
                "PUBLISHED"
                if channel and channel.is_active and integration.is_active and integration.status == "OK"
                else "DRAFT"
            ),
            allowed_origins=config.get("allowed_domains", []),
            presentation_config=presentation,
            consent_config={
                key: config[key]
                for key in ("consent_text", "consent_version")
                if key in config
            },
            anti_abuse_config={},
        )
        WebSession.objects.filter(connection_id=integration.id).update(widget_id=widget.id)


def remove_widgets(apps, schema_editor):
    apps.get_model("webchat", "WebChatWidget").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0005_integration_is_active"),
        ("webchat", "0003_alter_websession_organization"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebChatWidget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=64)),
                ("public_key", models.CharField(default=chatballs.webchat.models.generate_widget_public_key, editable=False, max_length=64, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("mode", models.CharField(choices=[("ANONYMOUS", "Анонимный"), ("AUTHENTICATED_PRODUCT", "Авторизованный продукт")], default="ANONYMOUS", max_length=32)),
                ("status", models.CharField(choices=[("DRAFT", "Черновик"), ("PUBLISHED", "Опубликован"), ("DISABLED", "Отключён")], default="DRAFT", max_length=16)),
                ("allowed_origins", models.JSONField(blank=True, default=list)),
                ("presentation_config", models.JSONField(blank=True, default=dict)),
                ("consent_config", models.JSONField(blank=True, default=dict)),
                ("anti_abuse_config", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("integration", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="web_chat_widget", to="integrations.integration")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="identity.organization")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="webchatwidget",
            constraint=models.UniqueConstraint(fields=("organization", "code"), name="uniq_web_chat_widget_org_code"),
        ),
        migrations.AddField(
            model_name="websession",
            name="widget",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sessions", to="webchat.webchatwidget"),
        ),
        migrations.RunPython(backfill_widgets, remove_widgets),
        migrations.AlterField(
            model_name="websession",
            name="widget",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sessions", to="webchat.webchatwidget"),
        ),
    ]
