from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ai", "0033_external_text_runtime")]
    operations = [migrations.AddField(
        model_name="externalagentbinding", name="processing_mode",
        field=models.CharField(max_length=8, default="ordinary", choices=[("ordinary", "ordinary"), ("long", "long")]),
    )]
