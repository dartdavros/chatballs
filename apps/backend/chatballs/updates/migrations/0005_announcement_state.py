from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("updates", "0004_check_in_version_schedule")]

    operations = [
        migrations.CreateModel(
            name="AnnouncementState",
            fields=[
                ("instance", models.OneToOneField(to="identity.instancesettings", primary_key=True,
                    serialize=False, on_delete=django.db.models.deletion.CASCADE)),
                ("revision", models.PositiveBigIntegerField()),
                ("publications", models.JSONField(default=list)),
                ("clock_offset_ms", models.BigIntegerField(default=0)),
            ],
        ),
    ]
