from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("webchat", "0010_web_recording_settings"),
        ("integrations", "0033_merge_speech_and_native")]
    operations = [migrations.CreateModel(name="SiteEventLaunch", fields=[
        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("rule_id", models.CharField(max_length=32)),
        ("rule_digest", models.CharField(max_length=64)),
        ("mode_version", models.PositiveBigIntegerField()),
        ("control_version", models.PositiveBigIntegerField(default=0)),
        ("agent_id_snapshot", models.PositiveBigIntegerField()),
        ("agent_version", models.CharField(max_length=64)),
        ("state", models.CharField(default="pending", max_length=16)),
        ("created_at", models.DateTimeField(auto_now_add=True)),
        ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="identity.organization")),
        ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="site_event_launches", to="webchat.websession")),
        ("receipt", models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to="integrations.eventreceipt")),
        ("conversation", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to="conversations.conversation")),
        ("response", models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to="conversations.message")),
    ], options={"constraints": [models.UniqueConstraint(fields=("session", "rule_id"), name="site_event_once_session_rule")]})]
