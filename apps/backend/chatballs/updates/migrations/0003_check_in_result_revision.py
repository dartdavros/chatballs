from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("updates", "0002_check_in_state")]

    operations = [
        migrations.AddField(
            model_name="checkinstate",
            name="last_result_revision",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
    ]
