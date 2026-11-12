from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("integrations", "0034_scenario_category_path")]

    operations = [
        migrations.AlterField(
            model_name="integration",
            name="provider",
            field=models.CharField(
                max_length=16,
                choices=[
                    ("YANDEX_SPEECHKIT", "Yandex SpeechKit"),
                    ("OPENAI", "OpenAI"),
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
            ),
        ),
    ]
