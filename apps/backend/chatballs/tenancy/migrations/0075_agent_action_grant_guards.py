"""Agent policies use the existing forced tenant RLS and FK guards."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLE = "integrations_agentactiongrant"
PARENTS = (("ai_aiagent", "agent_id"), ("integrations_integration", "integration_id"),
           ("integrations_scenariodefinition", "scenario_id"))


def forwards(apps, schema_editor):
    schema_editor.execute(guards.FORWARD_RLS.format(table=TABLE))
    for parent, column in PARENTS:
        schema_editor.execute(guards.FORWARD_TRIGGER.format(table=TABLE, parent=parent, column=column))


def backwards(apps, schema_editor):
    for _, column in PARENTS:
        schema_editor.execute(f"DROP TRIGGER {TABLE}_{column}_tenant ON {TABLE}")
    schema_editor.execute(f"""
        DROP POLICY chatballs_tenant_isolation ON {TABLE};
        DROP POLICY chatballs_schema_access ON {TABLE};
        ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY;
        REVOKE ALL ON TABLE {TABLE} FROM chatballs_runtime_app;
        REVOKE USAGE, SELECT ON SEQUENCE {TABLE}_id_seq FROM chatballs_runtime_app;
    """)


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0074_scenario_root_identity"), ("integrations", "0024_agent_action_grants")]
    operations = [migrations.RunPython(forwards, backwards)]
