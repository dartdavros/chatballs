from django.db import migrations


FORWARD_SQL = """
ALTER TABLE webchat_webchatwidget OWNER TO chatballs_schema;
ALTER TABLE webchat_webchatwidget ENABLE ROW LEVEL SECURITY;
ALTER TABLE webchat_webchatwidget FORCE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE webchat_webchatwidget FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON webchat_webchatwidget TO chatballs_runtime_app;
GRANT ALL ON webchat_webchatwidget TO chatballs_schema;
GRANT USAGE, SELECT ON SEQUENCE webchat_webchatwidget_id_seq
    TO chatballs_runtime_app, chatballs_schema;

CREATE POLICY chatballs_tenant_isolation ON webchat_webchatwidget
    FOR ALL TO chatballs_runtime_app
    USING (organization_id = chatballs.current_organization_id())
    WITH CHECK (organization_id = chatballs.current_organization_id());
CREATE POLICY chatballs_schema_access ON webchat_webchatwidget
    FOR ALL TO chatballs_schema USING (true) WITH CHECK (true);

CREATE CONSTRAINT TRIGGER wcw_integration
AFTER INSERT OR UPDATE ON webchat_webchatwidget
DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
chatballs.enforce_tenant_fk('integrations_integration', 'integration_id');

CREATE CONSTRAINT TRIGGER ws_widget
AFTER INSERT OR UPDATE ON webchat_websession
DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
chatballs.enforce_tenant_fk('webchat_webchatwidget', 'widget_id');

CREATE VIEW chatballs.web_widget_directory
WITH (security_barrier = true) AS
    SELECT widget.id AS resource_id,
           widget.organization_id,
           widget.public_key AS lookup_key
    FROM webchat_webchatwidget widget
    JOIN integrations_integration integration
      ON integration.id = widget.integration_id
     AND integration.organization_id = widget.organization_id
    JOIN channels_channel channel
      ON channel.id = integration.channel_id
     AND channel.organization_id = widget.organization_id
    WHERE widget.status = 'PUBLISHED'
      AND integration.provider = 'WEB'
      AND integration.status = 'OK'
      AND integration.is_active
      AND channel.is_active;
ALTER VIEW chatballs.web_widget_directory OWNER TO chatballs_schema;
REVOKE ALL ON chatballs.web_widget_directory FROM PUBLIC;
GRANT SELECT ON chatballs.web_widget_directory TO chatballs_runtime_platform;
"""


REVERSE_SQL = """
DROP VIEW IF EXISTS chatballs.web_widget_directory;
DROP TRIGGER IF EXISTS ws_widget ON webchat_websession;
DROP TRIGGER IF EXISTS wcw_integration ON webchat_webchatwidget;
DROP POLICY IF EXISTS chatballs_tenant_isolation ON webchat_webchatwidget;
DROP POLICY IF EXISTS chatballs_schema_access ON webchat_webchatwidget;
ALTER TABLE webchat_webchatwidget NO FORCE ROW LEVEL SECURITY;
ALTER TABLE webchat_webchatwidget DISABLE ROW LEVEL SECURITY;
REVOKE ALL ON webchat_webchatwidget FROM chatballs_runtime_app;
REVOKE USAGE, SELECT ON SEQUENCE webchat_webchatwidget_id_seq
    FROM chatballs_runtime_app;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0014_agent_portal_article_guards"),
        ("webchat", "0004_web_chat_widget"),
    ]
    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]
