from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("ai", "0030_aiagent_transcription_language"), ("integrations", "0033_merge_speech_and_native")]
    operations = [
        migrations.AddField(model_name="aiagent", name="synthesis_integration", field=models.ForeignKey(
            blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
            related_name="synthesizing_agents", to="integrations.integration")),
        migrations.AddField(model_name="aiagent", name="synthesis_model", field=models.CharField(blank=True, default="", max_length=128)),
        migrations.AddField(model_name="aiagent", name="synthesis_voice", field=models.CharField(blank=True, default="", max_length=64)),
    ]
