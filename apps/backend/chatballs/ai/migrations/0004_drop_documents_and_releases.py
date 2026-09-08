# ADR-CHATBALLS-0023: снос версионируемых документов и релизов после переноса данных (0003).

import django.db.models.deletion
from django.db import migrations, models


def delete_unlinked_fragments(apps, schema_editor):
    # Фрагменты не-активных версий не переносились — удаляем перед NOT NULL.
    KnowledgeFragment = apps.get_model("ai", "KnowledgeFragment")
    KnowledgeFragment.objects.filter(knowledge__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0003_flatten_agent_config"),
    ]

    operations = [
        migrations.RunPython(delete_unlinked_fragments, migrations.RunPython.noop),
        migrations.RemoveField(model_name="llminvocation", name="release"),
        migrations.RemoveConstraint(model_name="knowledgefragment", name="uniq_fragment_version_chunk"),
        migrations.RemoveField(model_name="knowledgefragment", name="version"),
        migrations.AlterField(
            model_name="knowledgefragment",
            name="knowledge",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="fragments",
                to="ai.knowledge",
            ),
        ),
        migrations.AlterModelOptions(
            name="knowledgefragment",
            options={"ordering": ["knowledge_id", "chunk_index"]},
        ),
        migrations.AddConstraint(
            model_name="knowledgefragment",
            constraint=models.UniqueConstraint(fields=("knowledge", "chunk_index"), name="uniq_fragment_knowledge_chunk"),
        ),
        migrations.DeleteModel(name="ReleaseKnowledgeVersion"),
        migrations.DeleteModel(name="ReleasePromptVersion"),
        migrations.DeleteModel(name="ChannelAIRelease"),
        migrations.DeleteModel(name="KnowledgeDocumentVersion"),
        migrations.DeleteModel(name="PromptDocumentVersion"),
        migrations.DeleteModel(name="KnowledgeDocument"),
        migrations.DeleteModel(name="PromptDocument"),
    ]
