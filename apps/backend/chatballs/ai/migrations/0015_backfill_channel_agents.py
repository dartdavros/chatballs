# ADR-CHATBALLS-0041 §4: агент и канал — одна сущность. Каждому каналу без AIAgent
# создаётся DRAFT-агент (AI не отвечает, поведение канала не меняется), чтобы
# карточка агента существовала для всех исторических каналов.
from django.db import migrations


def backfill_agents(apps, schema_editor):
    Channel = apps.get_model("channels", "Channel")
    AIAgent = apps.get_model("ai", "AIAgent")
    for channel in Channel.objects.filter(ai_agent__isnull=True).iterator():
        AIAgent.objects.create(
            # Историческая модель не наследует автоустановку organization из
            # TenantRelationModel.save — ключ проставляется явно.
            organization_id=channel.organization_id,
            channel=channel,
            name=channel.name,
            status="DRAFT",
            credential_mode="CUSTOAI",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0014_remove_knowledgedepartment_department_and_more"),
        ("channels", "0007_channel_group"),
    ]
    operations = [
        migrations.RunPython(backfill_agents, migrations.RunPython.noop),
    ]
