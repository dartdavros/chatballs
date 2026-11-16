"""RLS, tenant foreign keys, hashed-key routing and non-revivable generations."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLES = {
    "ai_externalagentconnection": (("integrations_integration", "integration_id"),),
    "ai_externalagentbinding": (("ai_externalagentconnection", "connection_id"), ("ai_aiagent", "agent_id")),
    "ai_externalagentsession": (("ai_externalagentconnection", "connection_id"), ("ai_aiagent", "agent_id"),
                                ("conversations_conversation", "conversation_id")),
}
VERSION_TABLES = ("identity_organization", "ai_aiagent", "ai_externalagentconnection", "ai_externalagentbinding")

VERSION_SQL = """
CREATE FUNCTION chatballs.external_agent_versions() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'identity_organization' THEN
        NEW.external_execution_version := OLD.external_execution_version
            + (NEW.external_execution_enabled IS DISTINCT FROM OLD.external_execution_enabled)::integer;
    ELSIF TG_TABLE_NAME = 'ai_aiagent' THEN
        NEW.execution_version := OLD.execution_version
            + (NEW.execution_mode IS DISTINCT FROM OLD.execution_mode)::integer;
    ELSIF TG_TABLE_NAME = 'ai_externalagentconnection' THEN
        IF NEW.deduplication_key IS DISTINCT FROM OLD.deduplication_key THEN
            RAISE EXCEPTION 'external_agent_deduplication_key_immutable' USING ERRCODE = '23514';
        END IF;
        NEW.revision := OLD.revision + 1;
        NEW.credential_version := OLD.credential_version
            + (NEW.inbound_key_hash IS DISTINCT FROM OLD.inbound_key_hash)::integer;
    ELSE
        NEW.revision := OLD.revision
            + ((NEW.connection_id, NEW.agent_id, NEW.external_agent_id, NEW.enabled) IS DISTINCT FROM
               (OLD.connection_id, OLD.agent_id, OLD.external_agent_id, OLD.enabled))::integer;
        NEW.policy_version := OLD.policy_version + 1;
    END IF;
    RETURN NEW;
END $$;
CREATE FUNCTION chatballs.external_agent_access_changed() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.settings, NEW.credentials, NEW.adapter_key, NEW.adapter_version, NEW.auth_method)
        IS DISTINCT FROM
       (OLD.settings, OLD.credentials, OLD.adapter_key, OLD.adapter_version, OLD.auth_method) THEN
        UPDATE ai_externalagentconnection SET checked_at = NULL, capabilities = '{}'::jsonb
            WHERE integration_id = NEW.integration_id;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER external_agent_access_changed AFTER UPDATE ON integrations_serviceconnectionsettings
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_agent_access_changed();
CREATE VIEW chatballs.external_agent_key_directory WITH (security_barrier=true) AS
    SELECT id AS resource_id, organization_id, inbound_key_hash::text AS lookup_key
        FROM ai_externalagentconnection WHERE inbound_key_hash IS NOT NULL;
ALTER VIEW chatballs.external_agent_key_directory OWNER TO chatballs_schema;
REVOKE ALL ON chatballs.external_agent_key_directory FROM PUBLIC;
GRANT SELECT ON chatballs.external_agent_key_directory TO chatballs_runtime_app;
"""


def forwards(apps, schema_editor):
    for table, relations in TABLES.items():
        schema_editor.execute(guards.FORWARD_RLS.format(table=table))
        for parent, column in relations:
            schema_editor.execute(guards.FORWARD_TRIGGER.format(table=table, parent=parent, column=column))
    schema_editor.execute(VERSION_SQL)
    for table in VERSION_TABLES:
        schema_editor.execute(f"""CREATE TRIGGER external_agent_versions BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION chatballs.external_agent_versions()""")


def backwards(apps, schema_editor):
    schema_editor.execute("DROP VIEW chatballs.external_agent_key_directory")
    schema_editor.execute("DROP TRIGGER external_agent_access_changed ON integrations_serviceconnectionsettings")
    schema_editor.execute("DROP FUNCTION chatballs.external_agent_access_changed()")
    for table in VERSION_TABLES:
        schema_editor.execute(f"DROP TRIGGER external_agent_versions ON {table}")
    schema_editor.execute("DROP FUNCTION chatballs.external_agent_versions()")
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
    dependencies = [("tenancy", "0080_site_event_guards"), ("ai", "0032_external_execution_configuration")]
    operations = [migrations.RunPython(forwards, backwards)]
