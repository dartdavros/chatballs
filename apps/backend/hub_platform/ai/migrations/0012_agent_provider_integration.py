# SPEC-HUB-0027 §9, ADR-HUB-0037 §8 — этап 5, шаги 1-2.
#
# BYOK-секрет переезжает с канала на агента. До сих пор credential_mode и model
# жили на AIAgent, а provider_integration — на Channel: одно решение было
# разделено между двумя таблицами, состояние credential_mode = BYOK при
# provider_integration = null достижимо структурно, а форма агента скрыто
# писала в канал.
#
# Данные копируются один в один: у каждого агента провайдер берётся из его
# канала. Channel.provider_integration на этом шаге сохраняется — резолвер
# один релиз падает на него для не мигрированных записей (§9 шаг 3), и
# удаляется отдельным шагом 6.
import django.db.models.deletion
from django.db import migrations, models
from django.db.models import OuterRef, Subquery


def copy_provider_to_agents(apps, schema_editor):
    AIAgent = apps.get_model("ai", "AIAgent")
    Channel = apps.get_model("channels", "Channel")
    # F() через join в update() Django не разрешает, поэтому подзапрос.
    AIAgent.objects.filter(channel__provider_integration__isnull=False).update(
        provider_integration_id=Subquery(
            Channel.objects.filter(pk=OuterRef("channel_id")).values(
                "provider_integration_id"
            )[:1]
        )
    )


def clear_agent_provider(apps, schema_editor):
    # Обратный шаг безопасен: источником истины на откате снова становится
    # Channel.provider_integration, который этой миграцией не изменялся.
    AIAgent = apps.get_model("ai", "AIAgent")
    AIAgent.objects.update(provider_integration_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0011_require_knowledge_category'),
        ('integrations', '0004_alter_integration_provider_email'),
        ('channels', '0005_enforce_policy_invariants'),
    ]

    operations = [
        migrations.AddField(
            model_name='aiagent',
            name='provider_integration',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='agents', to='integrations.integration'),
        ),
        migrations.RunPython(copy_provider_to_agents, clear_agent_provider),
    ]
