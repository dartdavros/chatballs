"""The diagnostic belongs to exactly the same tenant as its incoming message."""

from django.db import migrations


FORWARD = """
ALTER TABLE ai_turndiagnostic OWNER TO chatballs_schema;
ALTER TABLE ai_turndiagnostic ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_turndiagnostic FORCE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE ai_turndiagnostic FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE ai_turndiagnostic TO chatballs_runtime_app;
GRANT ALL ON TABLE ai_turndiagnostic TO chatballs_schema;
GRANT USAGE, SELECT ON SEQUENCE ai_turndiagnostic_id_seq TO chatballs_runtime_app, chatballs_schema;
CREATE POLICY chatballs_tenant_isolation ON ai_turndiagnostic
    FOR ALL TO chatballs_runtime_app
    USING (organization_id = chatballs.current_organization_id())
    WITH CHECK (organization_id = chatballs.current_organization_id());
CREATE POLICY chatballs_schema_access ON ai_turndiagnostic
    FOR ALL TO chatballs_schema USING (true) WITH CHECK (true);
CREATE CONSTRAINT TRIGGER diagnostic_message_tenant
AFTER INSERT OR UPDATE ON ai_turndiagnostic
DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
chatballs.enforce_tenant_fk('conversations_message', 'message_id');
"""
REVERSE = """
DROP TRIGGER diagnostic_message_tenant ON ai_turndiagnostic;
DROP POLICY chatballs_tenant_isolation ON ai_turndiagnostic;
DROP POLICY chatballs_schema_access ON ai_turndiagnostic;
ALTER TABLE ai_turndiagnostic NO FORCE ROW LEVEL SECURITY;
ALTER TABLE ai_turndiagnostic DISABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE ai_turndiagnostic FROM chatballs_runtime_app;
REVOKE USAGE, SELECT ON SEQUENCE ai_turndiagnostic_id_seq FROM chatballs_runtime_app;
"""


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0042_participant_guards"), ("ai", "0025_turndiagnostic")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
