"""Keep all three published/native tenant guard branches."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0077_merge_agent_and_automation_guards"),
        ("tenancy", "0075_native_action_receipt_guards"),
        ("integrations", "0030_merge_native_catalog"),
    ]
    operations = []
