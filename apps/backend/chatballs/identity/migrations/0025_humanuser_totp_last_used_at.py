from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0024_employeegroup_color"),
    ]

    operations = [
        migrations.AddField(
            model_name="humanuser",
            name="totp_last_used_at",
            field=models.DateTimeField(blank=True, db_default=None, null=True),
        ),
    ]
