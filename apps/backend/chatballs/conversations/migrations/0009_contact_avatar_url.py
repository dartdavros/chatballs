from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conversations", "0008_message_content_html"),
    ]

    operations = [
        migrations.AddField(
            model_name="contact",
            name="avatar_url",
            field=models.URLField(blank=True, default="", max_length=512),
        ),
    ]
