"""Route toggles and reconnection cannot revive an issued external authorization."""

from importlib import import_module

from django.db import migrations

version_function = import_module("chatballs.tenancy.migrations.0081_external_agent_configuration_guards").VERSION_SQL.split(
    "CREATE FUNCTION chatballs.external_agent_access_changed()", 1)[0].replace(
        "CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)

SQL = """
CREATE FUNCTION chatballs.external_route_revocation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'integrations_integration' THEN
        IF (NEW.is_active, NEW.channel_id, NEW.kind, NEW.provider) IS DISTINCT FROM
           (OLD.is_active, OLD.channel_id, OLD.kind, OLD.provider) THEN
            UPDATE ai_externalagentconnection c SET enabled = c.enabled
            WHERE c.integration_id = NEW.id OR c.id IN (
                SELECT s.connection_id FROM ai_externalagentsession s
                JOIN conversations_conversation v ON v.id = s.conversation_id
                WHERE v.connection_id = NEW.id);
        END IF;
    ELSIF TG_TABLE_NAME = 'channels_channel' THEN
        IF NEW.is_active IS DISTINCT FROM OLD.is_active THEN
            UPDATE ai_externalagentconnection c SET enabled = c.enabled
            WHERE c.id IN (SELECT b.connection_id FROM ai_externalagentbinding b
                JOIN ai_aiagent a ON a.id = b.agent_id WHERE a.channel_id = NEW.id);
        END IF;
    ELSIF TG_TABLE_NAME = 'conversations_conversation' THEN
        IF NEW.connection_id IS DISTINCT FROM OLD.connection_id THEN
            UPDATE ai_externalagentconnection c SET enabled = c.enabled
            WHERE c.id IN (SELECT s.connection_id FROM ai_externalagentsession s
                WHERE s.conversation_id = NEW.id);
        END IF;
    ELSE
        IF (NEW.status, NEW.channel_id) IS DISTINCT FROM (OLD.status, OLD.channel_id) THEN
            UPDATE ai_externalagentconnection c SET enabled = c.enabled
            WHERE c.id IN (SELECT b.connection_id FROM ai_externalagentbinding b WHERE b.agent_id = NEW.id);
        END IF;
    END IF;
    RETURN NEW;
END $$;
"""
TABLES = ("integrations_integration", "channels_channel", "conversations_conversation", "ai_aiagent")


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0081_external_agent_configuration_guards")]
    operations = [migrations.RunSQL(version_function, migrations.RunSQL.noop), migrations.RunSQL(SQL + "\n".join(
        f"CREATE TRIGGER external_route_revocation AFTER UPDATE ON {table} "
        "FOR EACH ROW EXECUTE FUNCTION chatballs.external_route_revocation();" for table in TABLES
    ), "\n".join(f"DROP TRIGGER external_route_revocation ON {table};" for table in TABLES)
        + "\nDROP FUNCTION chatballs.external_route_revocation();")]
