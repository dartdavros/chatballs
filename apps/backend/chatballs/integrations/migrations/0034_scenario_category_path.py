from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("integrations", "0033_merge_speech_and_native")]

    operations = [
        migrations.AddField(
            model_name="scenariodefinition",
            name="category_path",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
