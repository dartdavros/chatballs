from django.db import migrations


FORWARD_SQL = """
ALTER TABLE tenancy_storagereservation OWNER TO chatballs_schema;
ALTER TABLE tenancy_storagereservation ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy_storagereservation FORCE ROW LEVEL SECURITY;
REVOKE ALL ON tenancy_storagereservation FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON tenancy_storagereservation TO chatballs_runtime_app;
GRANT ALL ON tenancy_storagereservation TO chatballs_schema;
GRANT USAGE, SELECT ON SEQUENCE tenancy_storagereservation_id_seq
    TO chatballs_runtime_app, chatballs_schema;

DROP POLICY IF EXISTS chatballs_tenant_isolation ON tenancy_storagereservation;
CREATE POLICY chatballs_tenant_isolation ON tenancy_storagereservation
    FOR ALL TO chatballs_runtime_app
    USING (organization_id = chatballs.current_organization_id())
    WITH CHECK (organization_id = chatballs.current_organization_id());

DROP POLICY IF EXISTS chatballs_schema_access ON tenancy_storagereservation;
CREATE POLICY chatballs_schema_access ON tenancy_storagereservation
    FOR ALL TO chatballs_schema
    USING (true)
    WITH CHECK (true);
"""


REVERSE_SQL = """
DROP POLICY IF EXISTS chatballs_tenant_isolation ON tenancy_storagereservation;
DROP POLICY IF EXISTS chatballs_schema_access ON tenancy_storagereservation;
ALTER TABLE tenancy_storagereservation NO FORCE ROW LEVEL SECURITY;
ALTER TABLE tenancy_storagereservation DISABLE ROW LEVEL SECURITY;
REVOKE ALL ON tenancy_storagereservation FROM chatballs_runtime_app;
REVOKE USAGE, SELECT ON SEQUENCE tenancy_storagereservation_id_seq
    FROM chatballs_runtime_app;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0012_organization_settings_rls"),
    ]

    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]
