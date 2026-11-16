from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("integrations", "0035_integration_openai_provider")]
    operations = [migrations.AddField(
        model_name="integration", name="web_schema_generation",
        field=models.PositiveBigIntegerField(default=1, editable=False),
    )]
