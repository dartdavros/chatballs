from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("webchat", "0012_site_event_origin")]
    operations = [
        migrations.AddField(
            model_name="websession", name="greeting", field=models.TextField(blank=True, default=""),
        ),
    ]
