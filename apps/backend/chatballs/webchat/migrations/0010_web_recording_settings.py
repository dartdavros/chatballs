from django.db import migrations


def preserve_web_permissions(apps, schema_editor):
    Integration = apps.get_model("integrations", "Integration")
    for integration in Integration.objects.using(schema_editor.connection.alias).filter(provider="WEB").iterator():
        config = dict(integration.config)
        config.setdefault("microphoneMode", "voice_message" if integration.voice_messages_enabled else "off")
        config.setdefault("maxRecordingBytes", 10 * 1024 * 1024)
        config.setdefault("maxDictationSeconds", 60)
        integration.config = config
        integration.save(update_fields=["config"])


class Migration(migrations.Migration):
    dependencies = [("webchat", "0009_session_consent"), ("integrations", "0029_merge_agent_actions_and_automation")]
    operations = [migrations.RunPython(preserve_web_permissions, migrations.RunPython.noop)]
