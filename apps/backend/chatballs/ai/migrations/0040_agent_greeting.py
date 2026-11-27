from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ai", "0039_externalagentnotice")]
    operations = [
        migrations.AddField(
            model_name="aiagent", name="greeting",
            field=models.CharField(blank=True, default="", max_length=4000),
        ),
    ]
