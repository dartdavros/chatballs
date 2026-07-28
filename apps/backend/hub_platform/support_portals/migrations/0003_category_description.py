from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("support_portals", "0002_content_and_products")]

    operations = [
        migrations.AddField(
            model_name="portalcategory",
            name="description",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
