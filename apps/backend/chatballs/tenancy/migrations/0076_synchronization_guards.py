"""Entity links, native clocks and exchange checkpoints retain tenant isolation."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLES = {
    "integrations_entitylink": (("integrations_integration", "integration_id"),),
    "integrations_integrationentityversion": (),
    "integrations_synchronizationcheckpoint": (("integrations_servicesynchronizationsettings", "settings_id"),
        ("integrations_entitylink", "link_id"), ("integrations_scenariorun", "run_id")),
}


def forwards(apps, schema_editor):
    for table, relations in TABLES.items():
        schema_editor.execute(guards.FORWARD_RLS.format(table=table))
        for parent, column in relations:
            schema_editor.execute(guards.FORWARD_TRIGGER.format(table=table, parent=parent, column=column))
    schema_editor.execute(guards.FORWARD_TRIGGER.format(table="integrations_servicesynchronizationsettings", parent="identity_employeeprofile", column="delegate_id"))
    schema_editor.execute("""
        CREATE FUNCTION chatballs.integration_link_native_tenant() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE parent_org bigint;
        BEGIN
            IF NEW.internal_kind = 'contact' THEN
                SELECT organization_id INTO parent_org FROM conversations_contact WHERE id = NEW.internal_id;
            ELSIF NEW.internal_kind = 'conversation' THEN
                SELECT organization_id INTO parent_org FROM conversations_conversation WHERE id = NEW.internal_id;
            ELSE
                RAISE EXCEPTION 'Invalid native entity kind' USING ERRCODE = '23514';
            END IF;
            IF parent_org IS NULL OR parent_org <> NEW.organization_id THEN
                RAISE EXCEPTION 'Native entity outside tenant' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$;
        ALTER FUNCTION chatballs.integration_link_native_tenant() OWNER TO chatballs_schema;
        CREATE TRIGGER integration_link_native_tenant BEFORE INSERT OR UPDATE OF organization_id, internal_kind, internal_id
            ON integrations_entitylink FOR EACH ROW EXECUTE FUNCTION chatballs.integration_link_native_tenant();
    """)


def backwards(apps, schema_editor):
    schema_editor.execute("DROP TRIGGER integration_link_native_tenant ON integrations_entitylink")
    schema_editor.execute("DROP FUNCTION chatballs.integration_link_native_tenant()")
    schema_editor.execute("DROP TRIGGER integrations_servicesynchronizationsettings_delegate_id_tenant ON integrations_servicesynchronizationsettings")
    for table, relations in TABLES.items():
        for _, column in relations:
            schema_editor.execute(f"DROP TRIGGER {table}_{column}_tenant ON {table}")
        schema_editor.execute(f"""DROP POLICY chatballs_tenant_isolation ON {table};
            DROP POLICY chatballs_schema_access ON {table};
            ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
            ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
            REVOKE ALL ON TABLE {table} FROM chatballs_runtime_app;
            REVOKE USAGE, SELECT ON SEQUENCE {table}_id_seq FROM chatballs_runtime_app;""")


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0075_scenario_automation_guards"), ("integrations", "0026_synchronization_state")]
    operations = [migrations.RunPython(forwards, backwards)]
