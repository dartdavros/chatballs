"""Execution state has the same tenant guards as scenario configuration."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLES = {
    "integrations_scenariorun": (
        ("integrations_scenariodefinition", "scenario_id"),
        ("identity_employeeprofile", "initiator_id"),
        ("conversations_conversation", "conversation_id"),
    ),
    "integrations_scenariostep": (
        ("integrations_scenariorun", "run_id"), ("integrations_integration", "integration_id"),
    ),
    "integrations_runjournalentry": (("integrations_scenariorun", "run_id"),),
    "integrations_connectionexecutionlane": (
        ("integrations_scenariostep", "step_id"), ("integrations_integration", "integration_id"),
    ),
}


def forwards(apps, schema_editor):
    for table, relations in TABLES.items():
        schema_editor.execute(guards.FORWARD_RLS.format(table=table))
        for parent, column in relations:
            schema_editor.execute(guards.FORWARD_TRIGGER.format(table=table, parent=parent, column=column))


def backwards(apps, schema_editor):
    for table, relations in TABLES.items():
        for _parent, column in relations:
            schema_editor.execute(f"DROP TRIGGER {table}_{column}_tenant ON {table}")
        schema_editor.execute(f"""
            DROP POLICY chatballs_tenant_isolation ON {table};
            DROP POLICY chatballs_schema_access ON {table};
            ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
            ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
            REVOKE ALL ON TABLE {table} FROM chatballs_runtime_app;
            REVOKE USAGE, SELECT ON SEQUENCE {table}_id_seq FROM chatballs_runtime_app;
        """)


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0070_scenario_configuration_guards"), ("integrations", "0018_durable_service_runs")]
    operations = [migrations.RunPython(forwards, backwards)]
