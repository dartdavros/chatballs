from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conversations", "0007_conversation_transport_meta"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="content_html",
            field=models.TextField(blank=True),
        ),
    ]
