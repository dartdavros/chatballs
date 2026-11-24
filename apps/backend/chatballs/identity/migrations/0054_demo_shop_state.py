from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("identity", "0053_demo_reinstallation")]

    operations = [
        migrations.AddField(
            model_name="demodataset", name="shop_state",
            field=models.JSONField(default=dict, editable=False),
        ),
    ]
