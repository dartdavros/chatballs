from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("support_portals", "0005_custom_domain_verification_token")]

    operations = [
        migrations.AddField(
            model_name="supportportal",
            name="widget_channel",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="support_portal_widgets",
                to="channels.channel",
            ),
        ),
    ]
