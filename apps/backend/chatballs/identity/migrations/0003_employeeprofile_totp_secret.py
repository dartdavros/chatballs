from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0002_alter_humanuser_managers_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeeprofile",
            name="totp_secret",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
