"""RLS, cross-tenant guards and a narrow server-owned callback directory."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLES = {
    "integrations_scenarioprogress": (("integrations_scenariorun", "run_id"),),
    "integrations_scenariobudget": (("integrations_scenariorun", "root_id"),),
    "integrations_scenariowait": (("integrations_scenariorun", "run_id"),
        ("integrations_integration", "integration_id"), ("integrations_eventreceipt", "receipt_id")),
    "integrations_eventreceipt": (("integrations_integration", "integration_id"),),
}


def forwards(apps, schema_editor):
    for table, relations in TABLES.items():
        schema_editor.execute(guards.FORWARD_RLS.format(table=table))
        for parent, column in relations:
            schema_editor.execute(guards.FORWARD_TRIGGER.format(table=table, parent=parent, column=column))
    schema_editor.execute(guards.FORWARD_TRIGGER.format(
        table="integrations_scenariorun", parent="integrations_scenariorun", column="parent_id"))
    schema_editor.execute("""
        CREATE VIEW chatballs.service_event_directory WITH (security_barrier=true) AS
            SELECT id AS resource_id, organization_id, id::text AS lookup_key
            FROM integrations_integration WHERE kind = 'SERVICE';
        ALTER VIEW chatballs.service_event_directory OWNER TO chatballs_schema;
        REVOKE ALL ON chatballs.service_event_directory FROM PUBLIC;
        GRANT SELECT ON chatballs.service_event_directory TO chatballs_runtime_app;
    """)


def backwards(apps, schema_editor):
    schema_editor.execute("DROP VIEW chatballs.service_event_directory")
    schema_editor.execute("DROP TRIGGER integrations_scenariorun_parent_id_tenant ON integrations_scenariorun")
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
    dependencies = [("tenancy", "0072_execution_retention_grant_guards"),
                    ("integrations", "0022_eventreceipt_scenariobudget_scenarioprogress_and_more")]
    operations = [migrations.RunPython(forwards, backwards)]
