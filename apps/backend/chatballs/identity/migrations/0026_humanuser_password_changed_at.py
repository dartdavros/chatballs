from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0025_humanuser_totp_last_used_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="humanuser",
            name="password_changed_at",
            field=models.DateTimeField(blank=True, db_default=None, null=True),
        ),
    ]
