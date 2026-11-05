from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("webchat", "0011_site_event_launch")]
    operations = [migrations.AddField(
        model_name="siteeventlaunch", name="origin",
        field=models.CharField(default="", max_length=2048), preserve_default=False,
    )]
