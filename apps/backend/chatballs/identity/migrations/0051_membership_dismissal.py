from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("identity", "0050_external_checks")]

    operations = [
        migrations.AddField(
            model_name="organizationmembership", name="dismissed_at",
            field=models.DateTimeField(null=True, blank=True, default=None),
        ),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.CheckConstraint(
                condition=models.Q(dismissed_at__isnull=True)
                | (models.Q(blocked_at__isnull=False) & ~models.Q(role="OWNER")),
                name="dismissed_member_access_closed",
            ),
        ),
    ]
