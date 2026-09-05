from django.db import migrations, models

import hub_platform.identity.models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0022_demo_dataset_registry"),
    ]

    operations = [
        migrations.AddField(
            model_name="humanuser",
            name="avatar",
            field=models.FileField(blank=True, default="", max_length=512, storage=hub_platform.identity.models.user_storage, upload_to=hub_platform.identity.models.user_avatar_upload_path),
        ),
        migrations.AddField(
            model_name="humanuser",
            name="avatar_content_type",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
