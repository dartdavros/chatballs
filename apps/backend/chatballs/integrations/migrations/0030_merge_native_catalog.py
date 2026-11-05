"""Join published automation/agent policies with native action receipts."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0029_merge_agent_actions_and_automation"),
        ("integrations", "0024_native_action_grants_and_receipts"),
    ]
    operations = []
