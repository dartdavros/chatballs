"""Retention/file ownership and operation grants share tenant isolation."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLES = {
    "integrations_scenarioretentionpolicy": (),
    "integrations_stepoperationalfile": (
        ("integrations_scenariostep", "step_id"), ("integrations_servicefile", "file_id"),
    ),
    "integrations_actiongrant": (
        ("integrations_integration", "integration_id"), ("identity_employeeprofile", "membership_id"),
    ),
}


def forwards(apps, schema_editor):
    for table, relations in TABLES.items():
        schema_editor.execute(guards.FORWARD_RLS.format(table=table))
        for parent, column in relations:
            schema_editor.execute(guards.FORWARD_TRIGGER.format(table=table, parent=parent, column=column))
    schema_editor.execute("""
        CREATE FUNCTION chatballs.execution_identity_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.organization_id IS DISTINCT FROM OLD.organization_id THEN
                RAISE EXCEPTION 'execution tenant is immutable' USING ERRCODE = '23514';
            END IF;
            IF TG_TABLE_NAME = 'integrations_scenariorun' THEN
                IF NEW.public_id IS DISTINCT FROM OLD.public_id
                   OR NEW.scenario_key IS DISTINCT FROM OLD.scenario_key
                   OR NEW.trigger_key IS DISTINCT FROM OLD.trigger_key THEN
                    RAISE EXCEPTION 'run identity is immutable' USING ERRCODE = '23514';
                END IF;
            ELSE
                IF NEW.effect_key IS DISTINCT FROM OLD.effect_key
                   OR NEW.run_id IS DISTINCT FROM OLD.run_id
                   OR NEW.path IS DISTINCT FROM OLD.path
                   OR NEW.adapter_key IS DISTINCT FROM OLD.adapter_key
                   OR NEW.adapter_version IS DISTINCT FROM OLD.adapter_version
                   OR NEW.operation_key IS DISTINCT FROM OLD.operation_key
                   OR NEW.retry_strategy IS DISTINCT FROM OLD.retry_strategy
                   OR NEW.fence < OLD.fence THEN
                    RAISE EXCEPTION 'effect identity is immutable' USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NEW;
        END $$;
        ALTER FUNCTION chatballs.execution_identity_immutable() OWNER TO chatballs_schema;
        REVOKE ALL ON FUNCTION chatballs.execution_identity_immutable() FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION chatballs.execution_identity_immutable() TO chatballs_runtime_app;
        CREATE TRIGGER run_identity_immutable BEFORE UPDATE ON integrations_scenariorun
            FOR EACH ROW EXECUTE FUNCTION chatballs.execution_identity_immutable();
        CREATE TRIGGER step_identity_immutable BEFORE UPDATE ON integrations_scenariostep
            FOR EACH ROW EXECUTE FUNCTION chatballs.execution_identity_immutable();
    """)


def backwards(apps, schema_editor):
    schema_editor.execute("DROP TRIGGER run_identity_immutable ON integrations_scenariorun")
    schema_editor.execute("DROP TRIGGER step_identity_immutable ON integrations_scenariostep")
    schema_editor.execute("DROP FUNCTION chatballs.execution_identity_immutable()")
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
    dependencies = [("tenancy", "0071_scenario_execution_guards"), ("integrations", "0020_scenario_operation_grants")]
    operations = [migrations.RunPython(forwards, backwards)]
