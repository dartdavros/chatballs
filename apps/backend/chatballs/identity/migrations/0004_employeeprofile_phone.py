from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0003_employeeprofile_totp_secret"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeeprofile",
            name="phone",
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
