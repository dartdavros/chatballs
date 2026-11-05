"""The proactive once-rule marker has forced RLS and tenant-safe relations."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLE = "webchat_siteeventlaunch"
PARENTS = {"session_id": "webchat_websession", "receipt_id": "integrations_eventreceipt",
    "conversation_id": "conversations_conversation", "response_id": "conversations_message"}


def forwards(apps, schema_editor):
    schema_editor.execute(guards.FORWARD_RLS.format(table=TABLE))
    for column, parent in PARENTS.items():
        schema_editor.execute(guards.FORWARD_TRIGGER.format(table=TABLE, parent=parent, column=column))


def backwards(apps, schema_editor):
    for column in PARENTS:
        schema_editor.execute(f"DROP TRIGGER {TABLE}_{column}_tenant ON {TABLE}")
    schema_editor.execute(f"DROP POLICY chatballs_tenant_isolation ON {TABLE}")
    schema_editor.execute(f"DROP POLICY chatballs_schema_access ON {TABLE}")
    schema_editor.execute(f"ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY")
    schema_editor.execute(f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0079_native_agent_delegate_guard"), ("webchat", "0011_site_event_launch")]
    operations = [migrations.RunPython(forwards, backwards)]
