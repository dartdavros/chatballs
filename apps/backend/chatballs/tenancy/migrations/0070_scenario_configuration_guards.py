"""Tenant isolation for external keys and exchange configuration."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLES = {
    "integrations_scenarioexternalkey": (("integrations_scenariodefinition", "scenario_id"),),
    "integrations_servicesynchronizationsettings": (("integrations_integration", "integration_id"),),
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
    dependencies = [("tenancy", "0069_scenario_definition_guards"), ("integrations", "0017_scenario_external_keys_and_exchange")]
    operations = [migrations.RunPython(forwards, backwards)]
