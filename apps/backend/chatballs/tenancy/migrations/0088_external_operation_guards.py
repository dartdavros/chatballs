"""Tenant isolation and immutable content-free operation receipts."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLE = "ai_externalagentoperation"
SQL = """
CREATE FUNCTION chatballs.external_operation_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'external_operation_immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER external_operation_immutable BEFORE UPDATE ON ai_externalagentoperation
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_operation_immutable();
CREATE FUNCTION chatballs.external_operation_session_cleanup() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM ai_externalagentoperation WHERE session_id = OLD.id;
    RETURN OLD;
END $$;
CREATE TRIGGER external_operation_session_cleanup BEFORE DELETE ON ai_externalagentsession
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_operation_session_cleanup();
"""


def forwards(apps, schema_editor):
    schema_editor.execute(guards.FORWARD_RLS.format(table=TABLE))
    schema_editor.execute(guards.FORWARD_TRIGGER.format(
        table=TABLE, parent="ai_externalagentsession", column="session_id"))
    schema_editor.execute(SQL)


def backwards(apps, schema_editor):
    schema_editor.execute("""
        DROP TRIGGER external_operation_session_cleanup ON ai_externalagentsession;
        DROP FUNCTION chatballs.external_operation_session_cleanup();
        DROP TRIGGER external_operation_immutable ON ai_externalagentoperation;
        DROP FUNCTION chatballs.external_operation_immutable();
        DROP TRIGGER ai_externalagentoperation_session_id_tenant ON ai_externalagentoperation;
        DROP POLICY chatballs_tenant_isolation ON ai_externalagentoperation;
        DROP POLICY chatballs_schema_access ON ai_externalagentoperation;
        ALTER TABLE ai_externalagentoperation DISABLE ROW LEVEL SECURITY;
    """)


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0087_external_message_snapshot_guard"),
                    ("ai", "0037_external_proactive_operations")]
    operations = [migrations.RunPython(forwards, backwards)]
