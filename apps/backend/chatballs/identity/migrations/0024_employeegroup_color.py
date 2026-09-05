from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0023_humanuser_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeegroup",
            name="color",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
    ]
