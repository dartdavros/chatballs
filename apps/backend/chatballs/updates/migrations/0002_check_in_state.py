import django.db.models.deletion
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0050_external_checks"),
        ("updates", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CheckInState",
            fields=[
                ("instance", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    primary_key=True, serialize=False, to="identity.instancesettings",
                )),
                ("installation_id", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("next_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("attempt_id", models.UUIDField(blank=True, null=True)),
                ("announcements", models.JSONField(default=list)),
                ("received_at", models.DateTimeField(blank=True, null=True)),
                ("received_revision", models.PositiveBigIntegerField(blank=True, null=True)),
                ("last_error", models.CharField(blank=True, default="", max_length=32)),
            ],
        ),
        migrations.RunSQL(
            "GRANT SELECT, INSERT, UPDATE ON updates_checkinstate TO chatballs_runtime_app;",
            "REVOKE SELECT, INSERT, UPDATE ON updates_checkinstate FROM chatballs_runtime_app;",
        ),
    ]
