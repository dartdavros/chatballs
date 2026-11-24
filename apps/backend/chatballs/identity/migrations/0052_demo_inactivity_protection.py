from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("identity", "0051_membership_dismissal")]

    operations = [
        migrations.AddField(
            model_name="demorecord",
            name="protect_from_inactivity",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="demorecord",
            name="protect_from_inactivity",
            field=models.BooleanField(null=True, default=False),
        ),
    ]
