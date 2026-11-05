import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("integrations", "0030_merge_native_catalog")]

    operations = [
        migrations.AlterField(
            model_name="servicefile", name="integration",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name="service_files", to="integrations.integration"),
        ),
    ]
