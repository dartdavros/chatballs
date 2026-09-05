from django.db import migrations


UNCATEGORIZED_CATEGORY_NAME = "Без категории"


def backfill_knowledge_categories(apps, schema_editor):
    Organization = apps.get_model("identity", "Organization")
    Knowledge = apps.get_model("ai", "Knowledge")
    KnowledgeCategory = apps.get_model("ai", "KnowledgeCategory")
    database = schema_editor.connection.alias

    organization_ids = Organization.objects.using(database).values_list("id", flat=True)
    for organization_id in organization_ids.iterator():
        category, _ = KnowledgeCategory.objects.using(database).get_or_create(
            organization_id=organization_id,
            is_system=True,
            defaults={
                "name": UNCATEGORIZED_CATEGORY_NAME,
                "parent_id": None,
                "sort_order": 0,
            },
        )
        Knowledge.objects.using(database).filter(
            organization_id=organization_id,
            category__isnull=True,
        ).update(
            category_id=category.pk,
            visibility="ORGANIZATION",
        )

    if Knowledge.objects.using(database).filter(category__isnull=True).exists():
        raise RuntimeError("B03 knowledge category backfill left NULL rows")


class Migration(migrations.Migration):
    dependencies = [("ai", "0009_knowledge_hierarchy_and_visibility")]

    operations = [
        migrations.RunPython(backfill_knowledge_categories, migrations.RunPython.noop),
    ]
