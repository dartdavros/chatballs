from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("support_portals", "0012_article_curation")]

    operations = [
        migrations.AddField(
            model_name="portalcategory", name="is_system", field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name="portalcategory",
            constraint=models.UniqueConstraint(
                fields=("portal",), condition=models.Q(is_system=True),
                name="uniq_support_portal_system_category",
            ),
        ),
    ]
