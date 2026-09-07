# Файлы статей портала (support_portals_portalarticlefile): tenant-таблица с
# organization_id, RLS и триггером связи со статьёй по образцу tenancy/0010.
# Скачивание публичное по непредсказуемому UUID, поэтому строка попадает и в
# ingress-директорию — платформенная роль резолвит организацию по public_id.
from django.db import migrations

TABLE = "support_portals_portalarticlefile"

FORWARD_RLS = f"""
ALTER TABLE {TABLE} OWNER TO chatballs_schema;
ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE {TABLE} FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {TABLE} TO chatballs_runtime_app;
GRANT ALL ON TABLE {TABLE} TO chatballs_schema;
GRANT USAGE, SELECT ON SEQUENCE {TABLE}_id_seq
    TO chatballs_runtime_app, chatballs_runtime_platform, chatballs_schema;
DROP POLICY IF EXISTS chatballs_tenant_isolation ON {TABLE};
CREATE POLICY chatballs_tenant_isolation ON {TABLE}
    FOR ALL TO chatballs_runtime_app
    USING (organization_id = chatballs.current_organization_id())
    WITH CHECK (organization_id = chatballs.current_organization_id());
DROP POLICY IF EXISTS chatballs_schema_access ON {TABLE};
CREATE POLICY chatballs_schema_access ON {TABLE}
    FOR ALL TO chatballs_schema USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS sp_article_file_article ON {TABLE};
CREATE CONSTRAINT TRIGGER sp_article_file_article
AFTER INSERT OR UPDATE ON {TABLE}
DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
chatballs.enforce_tenant_fk('support_portals_portalarticle', 'article_id');

DROP TRIGGER IF EXISTS sp_article_file_user ON {TABLE};
CREATE CONSTRAINT TRIGGER sp_article_file_user
AFTER INSERT OR UPDATE ON {TABLE}
DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
chatballs.enforce_tenant_user('uploaded_by_id');

DROP TRIGGER IF EXISTS sp_revision_user ON support_portals_portalarticlerevision;
CREATE CONSTRAINT TRIGGER sp_revision_user
AFTER INSERT OR UPDATE ON support_portals_portalarticlerevision
DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
chatballs.enforce_tenant_user('created_by_id');

CREATE OR REPLACE VIEW chatballs.portal_article_file_directory
WITH (security_barrier = true) AS
    SELECT article_file.id AS resource_id,
           article_file.organization_id,
           article_file.public_id::text AS lookup_key
    FROM {TABLE} article_file;
ALTER VIEW chatballs.portal_article_file_directory OWNER TO chatballs_schema;
REVOKE ALL ON chatballs.portal_article_file_directory FROM PUBLIC;
GRANT SELECT ON chatballs.portal_article_file_directory TO chatballs_runtime_platform;
"""

REVERSE_RLS = f"""
DROP VIEW IF EXISTS chatballs.portal_article_file_directory;
DROP TRIGGER IF EXISTS sp_revision_user ON support_portals_portalarticlerevision;
DROP TRIGGER IF EXISTS sp_article_file_user ON {TABLE};
DROP TRIGGER IF EXISTS sp_article_file_article ON {TABLE};
DROP POLICY IF EXISTS chatballs_tenant_isolation ON {TABLE};
DROP POLICY IF EXISTS chatballs_schema_access ON {TABLE};
ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY;
ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0026_contact_merge_rls"),
        ("support_portals", "0010_article_files"),
    ]

    operations = [migrations.RunSQL(FORWARD_RLS, REVERSE_RLS)]
