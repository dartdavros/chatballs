"""Automation rows have tenant RLS; public routing exposes no credentials."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLES = {
    "integrations_scenarioautomation": (("integrations_scenariodefinition", "scenario_id"), ("identity_employeeprofile", "delegate_id")),
    "integrations_eventsubscription": (("integrations_scenariodefinition", "scenario_id"), ("integrations_integration", "integration_id")),
    "integrations_eventdelivery": (("integrations_eventreceipt", "receipt_id"), ("integrations_scenariodefinition", "scenario_id"), ("integrations_scenariorun", "run_id")),
    "integrations_schedulecheckpoint": (("integrations_scenariodefinition", "scenario_id"),),
    "integrations_pollcursor": (("integrations_integration", "integration_id"),),
}


def forwards(apps, schema_editor):
    for table, relations in TABLES.items():
        schema_editor.execute(guards.FORWARD_RLS.format(table=table))
        for parent, column in relations:
            schema_editor.execute(guards.FORWARD_TRIGGER.format(table=table, parent=parent, column=column))
    schema_editor.execute("""
        CREATE VIEW chatballs.scenario_trigger_directory WITH (security_barrier=true) AS
            SELECT id AS resource_id, organization_id, public_id::text AS lookup_key
            FROM integrations_scenarioexternalkey;
        ALTER VIEW chatballs.scenario_trigger_directory OWNER TO chatballs_schema;
        REVOKE ALL ON chatballs.scenario_trigger_directory FROM PUBLIC;
        GRANT SELECT ON chatballs.scenario_trigger_directory TO chatballs_runtime_app;
    """)


def backwards(apps, schema_editor):
    schema_editor.execute("DROP VIEW chatballs.scenario_trigger_directory")
    for table, relations in TABLES.items():
        for _, column in relations:
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
    dependencies = [("tenancy", "0074_scenario_root_identity"), ("integrations", "0024_durable_automation")]
    operations = [migrations.RunPython(forwards, backwards)]
