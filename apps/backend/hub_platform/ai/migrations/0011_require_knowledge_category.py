import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ai", "0010_backfill_knowledge_category")]

    operations = [
        migrations.AlterField(
            model_name="knowledge",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="knowledge_items",
                to="ai.knowledgecategory",
            ),
        ),
    ]
