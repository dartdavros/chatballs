from django.db import migrations, models


def preserve_rate_limits(apps, schema_editor):
    state = apps.get_model("updates", "CheckInState")
    state.objects.using(schema_editor.connection.alias).filter(last_error="http_429").update(rate_limited=True)


class Migration(migrations.Migration):
    dependencies = [("updates", "0003_check_in_result_revision")]

    operations = [
        migrations.AddField(
            model_name="checkinstate",
            name="last_attempted_version",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="checkinstate",
            name="rate_limited",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(preserve_rate_limits, migrations.RunPython.noop),
    ]
