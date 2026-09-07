from django.db import migrations


# Таблица support_portals_supportportalproduct удалена вместе с сущностью
# Product (ADR-HUB-0045); на старых БД её снимает 0029_drop_product_support.
TABLES = (
    "support_portals_supportportal",
    "support_portals_portalcategory",
    "support_portals_portalarticle",
    "support_portals_portalarticlerevision",
    "support_portals_portalarticlefeedback",
)

RELATIONS = (
    ("sp_portal_department", TABLES[0], "identity_department", "department_id"),
    ("sp_category_portal", TABLES[1], TABLES[0], "portal_id"),
    ("sp_category_parent", TABLES[1], TABLES[1], "parent_id"),
    ("sp_article_portal", TABLES[2], TABLES[0], "portal_id"),
    ("sp_article_category", TABLES[2], TABLES[1], "category_id"),
    ("sp_article_revision", TABLES[2], TABLES[3], "published_revision_id"),
    ("sp_revision_article", TABLES[3], TABLES[2], "article_id"),
    ("sp_feedback_article", TABLES[4], TABLES[2], "article_id"),
)


def install(apps, schema_editor):
    # Runtime roles must never inherit the permissive schema-owner RLS policy.
    # Fresh clusters enforce this in init-runtime-roles.sh; the migration also
    # repairs upgraded clusters created before that guard existed.
    schema_editor.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_auth_members membership
                JOIN pg_roles parent ON parent.oid = membership.roleid
                JOIN pg_roles child ON child.oid = membership.member
                WHERE parent.rolname = 'chatballs_schema'
                  AND child.rolname IN (
                      'chatballs_runtime_app',
                      'chatballs_runtime_platform'
                  )
            ) THEN
                REVOKE chatballs_schema
                    FROM chatballs_runtime_app, chatballs_runtime_platform;
            END IF;
        END
        $$;
        """
    )
    for table in TABLES:
        schema_editor.execute(
            f"""
            ALTER TABLE {table} OWNER TO chatballs_schema;
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            REVOKE ALL ON TABLE {table} FROM PUBLIC;
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO chatballs_runtime_app;
            GRANT ALL ON TABLE {table} TO chatballs_schema;
            CREATE POLICY chatballs_tenant_isolation ON {table}
                FOR ALL TO chatballs_runtime_app
                USING (organization_id = chatballs.current_organization_id())
                WITH CHECK (organization_id = chatballs.current_organization_id());
            CREATE POLICY chatballs_schema_access ON {table}
                FOR ALL TO chatballs_schema USING (true) WITH CHECK (true);
            """
        )
    for trigger, child, parent, column in RELATIONS:
        schema_editor.execute(
            f"""
            CREATE CONSTRAINT TRIGGER {trigger}
            AFTER INSERT OR UPDATE ON {child}
            DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
            chatballs.enforce_tenant_fk('{parent}', '{column}');
            """
        )
    schema_editor.execute(
        """
        CREATE OR REPLACE VIEW chatballs.support_portal_directory
        WITH (security_barrier = true) AS
            SELECT portal.id AS resource_id,
                   portal.organization_id,
                   portal.slug AS lookup_key
            FROM support_portals_supportportal portal
            JOIN identity_department department
              ON department.id = portal.department_id
             AND department.organization_id = portal.organization_id
            WHERE portal.status = 'PUBLISHED'
              AND department.code = 'support';
        ALTER VIEW chatballs.support_portal_directory OWNER TO chatballs_schema;
        REVOKE ALL ON chatballs.support_portal_directory FROM PUBLIC;
        GRANT SELECT ON chatballs.support_portal_directory TO chatballs_runtime_platform;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public
            TO chatballs_runtime_app, chatballs_runtime_platform, chatballs_schema;
        """
    )


def uninstall(apps, schema_editor):
    schema_editor.execute("DROP VIEW IF EXISTS chatballs.support_portal_directory")
    for trigger, child, _parent, _column in RELATIONS:
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {child}")
    for table in TABLES:
        schema_editor.execute(
            f"""
            DROP POLICY IF EXISTS chatballs_tenant_isolation ON {table};
            DROP POLICY IF EXISTS chatballs_schema_access ON {table};
            ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
            ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0009_tenant_guards_security_definer"),
        ("support_portals", "0002_content_and_products"),
    ]
    operations = [migrations.RunPython(install, uninstall)]
