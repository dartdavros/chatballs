from django.db import migrations, models


class Migration(migrations.Migration):
    """Язык ответов агента.

    Существующие агенты получают MIRROR — ответ на языке обращения. Для
    одноязычной установки это ничего не меняет: клиенты пишут на её языке, и
    агент отвечает так же. Для двуязычной — сразу перестаёт отвечать не на том
    языке, на котором спросили.
    """

    dependencies = [
        ("ai", "0016_remove_credential_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="aiagent",
            name="answer_language",
            field=models.CharField(default="MIRROR", max_length=16),
        ),
    ]
