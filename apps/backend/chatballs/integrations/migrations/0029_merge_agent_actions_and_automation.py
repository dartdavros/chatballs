"""Join independently applied agent and automation migration histories."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0024_agent_action_grants"),
        ("integrations", "0028_fanout_delivery_lease"),
    ]

    operations = []
