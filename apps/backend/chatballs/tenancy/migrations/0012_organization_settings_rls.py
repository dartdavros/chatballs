from django.db import migrations


FORWARD_SQL = """
ALTER TABLE identity_organization OWNER TO chatballs_schema;
ALTER TABLE identity_organization ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_organization FORCE ROW LEVEL SECURITY;
REVOKE ALL ON identity_organization FROM PUBLIC;

GRANT SELECT, UPDATE ON identity_organization TO chatballs_runtime_app;
GRANT SELECT, INSERT, UPDATE ON identity_organization TO chatballs_runtime_platform;
GRANT ALL ON identity_organization TO chatballs_schema;

DROP POLICY IF EXISTS chatballs_organization_app_select ON identity_organization;
CREATE POLICY chatballs_organization_app_select ON identity_organization
    FOR SELECT TO chatballs_runtime_app
    USING (true);

DROP POLICY IF EXISTS chatballs_organization_app_update ON identity_organization;
CREATE POLICY chatballs_organization_app_update ON identity_organization
    FOR UPDATE TO chatballs_runtime_app
    USING (id = chatballs.current_organization_id())
    WITH CHECK (id = chatballs.current_organization_id());

DROP POLICY IF EXISTS chatballs_organization_platform ON identity_organization;
CREATE POLICY chatballs_organization_platform ON identity_organization
    FOR ALL TO chatballs_runtime_platform
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS chatballs_organization_schema ON identity_organization;
CREATE POLICY chatballs_organization_schema ON identity_organization
    FOR ALL TO chatballs_schema
    USING (true)
    WITH CHECK (true);
"""


REVERSE_SQL = """
DROP POLICY IF EXISTS chatballs_organization_app_select ON identity_organization;
DROP POLICY IF EXISTS chatballs_organization_app_update ON identity_organization;
DROP POLICY IF EXISTS chatballs_organization_platform ON identity_organization;
DROP POLICY IF EXISTS chatballs_organization_schema ON identity_organization;
ALTER TABLE identity_organization NO FORCE ROW LEVEL SECURITY;
ALTER TABLE identity_organization DISABLE ROW LEVEL SECURITY;
REVOKE UPDATE ON identity_organization FROM chatballs_runtime_app;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0017_organization_branding"),
        ("tenancy", "0011_support_portal_host_directory"),
    ]

    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]
