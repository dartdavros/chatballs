from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0002_integration_channel_integration_poll_marker"),
    ]

    operations = [
        migrations.AlterField(
            model_name="integration",
            name="provider",
            field=models.CharField(
                choices=[
                    ("OPENROUTER", "OpenRouter"),
                    ("CUSTOM", "Custom (OpenAI-compatible)"),
                    ("MAX", "MAX"),
                    ("TELEGRAM", "Telegram"),
                    ("WEB", "Web-виджет"),
                ],
                max_length=16,
            ),
        ),
    ]
