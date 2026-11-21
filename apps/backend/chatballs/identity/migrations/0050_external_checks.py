from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("identity", "0049_external_execution_configuration")]

    operations = [
        migrations.AddField(
            model_name="instancesettings",
            name="external_checks_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="instancesettings",
            name="external_checks_revision",
            field=models.PositiveBigIntegerField(default=0),
        ),
    ]
