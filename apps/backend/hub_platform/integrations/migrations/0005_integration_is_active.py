from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0004_alter_integration_provider_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="integration",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
