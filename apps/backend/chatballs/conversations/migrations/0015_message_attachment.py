import chatballs.conversations.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conversations", "0014_contact_card_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="attachment",
            field=models.FileField(blank=True, max_length=512, upload_to=chatballs.conversations.models.message_attachment_upload_path),
        ),
        migrations.AddField(model_name="message", name="attachment_name", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="message", name="attachment_content_type", field=models.CharField(blank=True, max_length=128)),
        migrations.AddField(model_name="message", name="attachment_size", field=models.PositiveBigIntegerField(default=0)),
    ]
