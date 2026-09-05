from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conversations", "0013_message_conv_message_text_fts"),
    ]

    operations = [
        migrations.AddField(model_name="contact", name="description", field=models.TextField(blank=True, default="")),
        migrations.AddField(model_name="contact", name="company", field=models.CharField(blank=True, default="", max_length=160)),
        migrations.AddField(model_name="contact", name="city", field=models.CharField(blank=True, default="", max_length=120)),
    ]
