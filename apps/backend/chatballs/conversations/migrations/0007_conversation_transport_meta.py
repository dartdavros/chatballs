from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conversations", "0006_alter_connectionidentity_organization_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="transport_meta",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
