from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0006_integration_demo_provider"),
    ]

    operations = [
        migrations.AddField(model_name="integration", name="voice_messages_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="integration", name="audio_calls_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="integration", name="video_calls_enabled", field=models.BooleanField(default=True)),
    ]
