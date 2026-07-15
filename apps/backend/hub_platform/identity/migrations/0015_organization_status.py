# Generated for C06 tenant provisioning (SPEC-HUB-0021 §6/§8).
# Adds Organization.status and backfills existing organizations to ACTIVE.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0014_alter_accessprofilecapability_organization_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="status",
            field=models.CharField(
                choices=[("ACTIVE", "Active"), ("PENDING_OWNER", "Pending owner")],
                default="ACTIVE",
                max_length=32,
            ),
        ),
        # Existing organizations (e.g. Edevs) are treated as already active.
        migrations.RunSQL(
            sql="UPDATE identity_organization SET status = 'ACTIVE' WHERE status IS NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
