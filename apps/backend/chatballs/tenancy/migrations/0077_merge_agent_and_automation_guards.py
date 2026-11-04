"""Join tenant guards without rewriting either applied history."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0075_agent_action_grant_guards"),
        ("tenancy", "0076_synchronization_guards"),
    ]

    operations = []
