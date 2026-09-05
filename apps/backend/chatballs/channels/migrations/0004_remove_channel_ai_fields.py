# ADR-HUB-0023: AI-поведение канала (модель, промпт) переехало на агента.
# Выполняется после ai/0003, которая переносит system_prompt/model в агентов.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("channels", "0003_channel_allow_anonymous_sessions_and_more"),
        ("ai", "0003_flatten_agent_config"),
    ]

    operations = [
        migrations.RemoveField(model_name="channel", name="system_prompt"),
        migrations.RemoveField(model_name="channel", name="model"),
        migrations.RemoveField(model_name="channel", name="model_params"),
    ]
