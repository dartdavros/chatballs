import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("support_portals", "0004_portal_domains"),
    ]

    operations = [
        migrations.AddField(
            model_name="supportportal",
            name="custom_domain_verification_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
