from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0003_alter_integration_provider"),
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
                    ("EMAIL", "Email (IMAP/SMTP)"),
                ],
                max_length=16,
            ),
        ),
    ]
