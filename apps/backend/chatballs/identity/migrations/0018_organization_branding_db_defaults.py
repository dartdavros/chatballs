from django.db import migrations, models

import chatballs.identity.models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0017_organization_branding"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="logo",
            field=models.FileField(
                blank=True,
                db_default="",
                default="",
                max_length=512,
                upload_to=chatballs.identity.models.organization_logo_upload_path,
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="logo_content_type",
            field=models.CharField(
                blank=True,
                db_default="",
                default="",
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="logo_size",
            field=models.PositiveBigIntegerField(db_default=0, default=0),
        ),
    ]
