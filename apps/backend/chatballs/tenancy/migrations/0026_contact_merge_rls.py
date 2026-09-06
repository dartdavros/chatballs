from django.db import migrations


FORWARD_SQL = """
ALTER TABLE conversations_contactmerge OWNER TO chatballs_schema;
ALTER TABLE conversations_contactmerge ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations_contactmerge FORCE ROW LEVEL SECURITY;
REVOKE ALL ON conversations_contactmerge FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON conversations_contactmerge TO chatballs_runtime_app;
GRANT ALL ON conversations_contactmerge TO chatballs_schema;
GRANT USAGE, SELECT ON SEQUENCE conversations_contactmerge_id_seq
    TO chatballs_runtime_app, chatballs_schema;

DROP POLICY IF EXISTS chatballs_tenant_isolation ON conversations_contactmerge;
CREATE POLICY chatballs_tenant_isolation ON conversations_contactmerge
    FOR ALL TO chatballs_runtime_app
    USING (organization_id = chatballs.current_organization_id())
    WITH CHECK (organization_id = chatballs.current_organization_id());

DROP POLICY IF EXISTS chatballs_schema_access ON conversations_contactmerge;
CREATE POLICY chatballs_schema_access ON conversations_contactmerge
    FOR ALL TO chatballs_schema
    USING (true)
    WITH CHECK (true);
"""


REVERSE_SQL = """
DROP POLICY IF EXISTS chatballs_tenant_isolation ON conversations_contactmerge;
DROP POLICY IF EXISTS chatballs_schema_access ON conversations_contactmerge;
ALTER TABLE conversations_contactmerge NO FORCE ROW LEVEL SECURITY;
ALTER TABLE conversations_contactmerge DISABLE ROW LEVEL SECURITY;
REVOKE ALL ON conversations_contactmerge FROM chatballs_runtime_app;
REVOKE USAGE, SELECT ON SEQUENCE conversations_contactmerge_id_seq
    FROM chatballs_runtime_app;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0025_storage_settings"),
        ("conversations", "0018_contact_merge"),
    ]

    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]
