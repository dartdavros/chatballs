from django.db import migrations, models

import hub_platform.identity.models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0016_channel_capabilities"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="logo",
            field=models.FileField(
                blank=True,
                max_length=512,
                upload_to=hub_platform.identity.models.organization_logo_upload_path,
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="logo_content_type",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="organization",
            name="logo_size",
            field=models.PositiveBigIntegerField(default=0),
        ),
    ]
