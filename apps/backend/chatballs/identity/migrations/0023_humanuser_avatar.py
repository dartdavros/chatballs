from django.db import migrations, models

import chatballs.identity.models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0022_demo_dataset_registry"),
    ]

    operations = [
        migrations.AddField(
            model_name="humanuser",
            name="avatar",
            field=models.FileField(blank=True, default="", max_length=512, storage=chatballs.identity.models.user_storage, upload_to=chatballs.identity.models.user_avatar_upload_path),
        ),
        migrations.AddField(
            model_name="humanuser",
            name="avatar_content_type",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
