"""Root identity is immutable and stays in the same organization."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")


def forwards(apps, schema_editor):
    schema_editor.execute(guards.FORWARD_TRIGGER.format(
        table="integrations_scenariorun", parent="integrations_scenariorun", column="root_id"))
    schema_editor.execute("""
        CREATE FUNCTION chatballs.scenario_parent_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.parent_id IS DISTINCT FROM OLD.parent_id
               OR NEW.root_id IS DISTINCT FROM OLD.root_id
               OR NEW.call_path IS DISTINCT FROM OLD.call_path THEN
                RAISE EXCEPTION 'scenario ancestry is immutable' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$;
        ALTER FUNCTION chatballs.scenario_parent_immutable() OWNER TO chatballs_schema;
        REVOKE ALL ON FUNCTION chatballs.scenario_parent_immutable() FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION chatballs.scenario_parent_immutable() TO chatballs_runtime_app;
        CREATE TRIGGER scenario_parent_immutable BEFORE UPDATE ON integrations_scenariorun
            FOR EACH ROW EXECUTE FUNCTION chatballs.scenario_parent_immutable();
    """)


def backwards(apps, schema_editor):
    schema_editor.execute("DROP TRIGGER scenario_parent_immutable ON integrations_scenariorun")
    schema_editor.execute("DROP FUNCTION chatballs.scenario_parent_immutable()")
    schema_editor.execute("DROP TRIGGER integrations_scenariorun_root_id_tenant ON integrations_scenariorun")


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0073_composite_scenario_guards"),
                    ("integrations", "0023_scenariobudget_payload_bytes_and_more")]
    operations = [migrations.RunPython(forwards, backwards)]
