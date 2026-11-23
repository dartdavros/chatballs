from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("updates", "0006_announcement_runtime_permissions")]

    operations = [
        migrations.AddField(
            model_name="checkinstate", name="announcement_retry_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
