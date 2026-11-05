from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("webchat", "0008_observation_change_times")]

    operations = [
        migrations.AddField(
            model_name="websession", name="consent_version",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="websession", name="consent_accepted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="websession", name="consent_form_revision",
            field=models.CharField(max_length=64, blank=True, default=""),
        ),
    ]
