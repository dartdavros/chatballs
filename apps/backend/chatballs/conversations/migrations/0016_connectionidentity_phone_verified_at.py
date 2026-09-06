from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conversations", "0015_message_attachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="connectionidentity",
            name="phone_verified_at",
            field=models.DateTimeField(blank=True, db_default=None, null=True),
        ),
    ]
