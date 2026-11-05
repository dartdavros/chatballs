"""Native receipts have the same forced tenant boundary as run checkpoints."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLE = "integrations_nativeeffectreceipt"


def forwards(apps, schema_editor):
    schema_editor.execute(guards.FORWARD_RLS.format(table=TABLE))
    schema_editor.execute(guards.FORWARD_TRIGGER.format(table=TABLE,
        parent="integrations_scenariostep", column="step_id"))


def backwards(apps, schema_editor):
    schema_editor.execute(f"DROP TRIGGER {TABLE}_step_id_tenant ON {TABLE}")
    schema_editor.execute(f"DROP POLICY chatballs_tenant_isolation ON {TABLE}")
    schema_editor.execute(f"DROP POLICY chatballs_schema_access ON {TABLE}")
    schema_editor.execute(f"ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY")
    schema_editor.execute(f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0074_scenario_root_identity"),
        ("integrations", "0024_native_action_grants_and_receipts")]
    operations = [migrations.RunPython(forwards, backwards)]
