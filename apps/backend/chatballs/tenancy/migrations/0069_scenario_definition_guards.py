"""Scenario definitions and their connections use the existing tenant guards."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLES = {
    "integrations_scenariodefinition": (),
    "integrations_scenarioconnection": (
        ("integrations_scenariodefinition", "scenario_id"),
        ("integrations_integration", "integration_id"),
    ),
}


def forwards(apps, schema_editor):
    for table, relations in TABLES.items():
        schema_editor.execute(guards.FORWARD_RLS.format(table=table))
        for parent, column in relations:
            schema_editor.execute(guards.FORWARD_TRIGGER.format(table=table, parent=parent, column=column))
    schema_editor.execute("""
        CREATE FUNCTION chatballs.scenario_owner_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.organization_id IS DISTINCT FROM OLD.organization_id
                OR NEW.public_id IS DISTINCT FROM OLD.public_id THEN
                RAISE EXCEPTION 'scenario ownership is immutable' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$;
        ALTER FUNCTION chatballs.scenario_owner_immutable() OWNER TO chatballs_schema;
        REVOKE ALL ON FUNCTION chatballs.scenario_owner_immutable() FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION chatballs.scenario_owner_immutable() TO chatballs_runtime_app;
        CREATE TRIGGER scenario_owner_immutable BEFORE UPDATE ON integrations_scenariodefinition
            FOR EACH ROW EXECUTE FUNCTION chatballs.scenario_owner_immutable();
    """)


def backwards(apps, schema_editor):
    schema_editor.execute("DROP TRIGGER scenario_owner_immutable ON integrations_scenariodefinition")
    schema_editor.execute("DROP FUNCTION chatballs.scenario_owner_immutable()")
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
    dependencies = [("tenancy", "0068_service_connection_guards"), ("integrations", "0016_scenario_definitions")]
    operations = [migrations.RunPython(forwards, backwards)]
