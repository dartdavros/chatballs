# ADR-CHATBALLS-0023: перенос данных из версионируемых документов и релизов в
# плоские Знания и поля агента.
#
# - KnowledgeDocument -> Knowledge (содержимое последней опубликованной версии,
#   иначе последней; фрагменты этой версии перевешиваются на знание);
# - активный релиз канала -> выбор знаний агента (M2M) и склейка prompt-документов
#   в поле instructions (system -> qualification -> sales_behavior -> operator_handoff);
# - каналы с живым system_prompt без агента получают агента, чтобы AI-поведение
#   не потерялось при удалении channel.system_prompt (channels/0004).

from django.db import migrations

_PROMPT_ORDER = ("SYSTEM", "QUALIFICATION", "SALES_BEHAVIOR", "OPERATOR_HANDOFF")


def forwards(apps, schema_editor):
    Knowledge = apps.get_model("ai", "Knowledge")
    KnowledgeDocument = apps.get_model("ai", "KnowledgeDocument")
    KnowledgeFragment = apps.get_model("ai", "KnowledgeFragment")
    AIAgent = apps.get_model("ai", "AIAgent")
    ChannelAIRelease = apps.get_model("ai", "ChannelAIRelease")
    Channel = apps.get_model("channels", "Channel")

    knowledge_by_document: dict[int, int] = {}
    for document in KnowledgeDocument.objects.prefetch_related("versions"):
        versions = sorted(document.versions.all(), key=lambda item: item.version, reverse=True)
        version = next((item for item in versions if item.status == "PUBLISHED"), versions[0] if versions else None)
        knowledge = Knowledge.objects.create(
            organization_id=document.organization_id,
            title=document.title,
            content=version.content if version is not None else "",
            is_enabled=document.is_enabled,
        )
        knowledge_by_document[document.id] = knowledge.id
        if version is not None:
            KnowledgeFragment.objects.filter(version_id=version.id).update(knowledge_id=knowledge.id)

    for channel in Channel.objects.all():
        release = (
            ChannelAIRelease.objects.filter(channel_id=channel.id, status="PUBLISHED")
            .order_by("-version")
            .first()
        )
        agent = AIAgent.objects.filter(channel_id=channel.id).first()
        system_prompt = (channel.system_prompt or "").strip()
        if agent is None:
            if release is None and not system_prompt:
                continue
            agent = AIAgent.objects.create(
                channel_id=channel.id,
                name=f"{channel.name} Agent",
                is_active=True,
                model=channel.model,
                model_params=channel.model_params or {},
            )
        if release is not None:
            knowledge_ids = [
                knowledge_by_document[link.knowledge_version.document_id]
                for link in release.knowledge_versions.select_related("knowledge_version")
                if link.knowledge_version.document_id in knowledge_by_document
            ]
            if knowledge_ids:
                agent.knowledge_items.add(*knowledge_ids)
            if not (agent.instructions or "").strip():
                by_category = {
                    link.prompt_version.document.category: link.prompt_version.content
                    for link in release.prompt_versions.select_related("prompt_version__document")
                }
                agent.instructions = "\n\n".join(
                    by_category[category] for category in _PROMPT_ORDER if by_category.get(category, "").strip()
                )
            # Канал с опубликованным релизом был рабочим — агент остаётся включён.
            agent.is_active = True
        if not (agent.instructions or "").strip() and system_prompt:
            agent.instructions = system_prompt
        agent.save()


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0002_knowledge_and_agent_instructions"),
        ("channels", "0003_channel_allow_anonymous_sessions_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
