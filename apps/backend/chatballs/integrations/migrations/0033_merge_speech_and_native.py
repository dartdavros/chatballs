"""Join SpeechKit registration with the published native action migrations."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0030_alter_integration_kind_alter_integration_provider"),
        ("integrations", "0032_native_agent_delegates"),
    ]

    operations = []
