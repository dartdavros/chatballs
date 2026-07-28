from django.db import migrations


TABLES = (
    "support_portals_supportportal",
    "support_portals_supportportalproduct",
    "support_portals_portalcategory",
    "support_portals_portalarticle",
    "support_portals_portalarticlerevision",
    "support_portals_portalarticlefeedback",
)

RELATIONS = (
    ("sp_portal_department", TABLES[0], "identity_department", "department_id"),
    ("sp_product_portal", TABLES[1], TABLES[0], "portal_id"),
    ("sp_product_product", TABLES[1], "identity_product", "product_id"),
    ("sp_product_channel", TABLES[1], "channels_channel", "support_channel_id"),
    ("sp_category_portal", TABLES[2], TABLES[0], "portal_id"),
    ("sp_category_parent", TABLES[2], TABLES[2], "parent_id"),
    ("sp_article_portal", TABLES[3], TABLES[0], "portal_id"),
    ("sp_article_category", TABLES[3], TABLES[2], "category_id"),
    ("sp_article_revision", TABLES[3], TABLES[4], "published_revision_id"),
    ("sp_revision_article", TABLES[4], TABLES[3], "article_id"),
    ("sp_feedback_article", TABLES[5], TABLES[3], "article_id"),
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
                WHERE parent.rolname = 'custocrm_schema'
                  AND child.rolname IN (
                      'custocrm_runtime_app',
                      'custocrm_runtime_platform'
                  )
            ) THEN
                REVOKE custocrm_schema
                    FROM custocrm_runtime_app, custocrm_runtime_platform;
            END IF;
        END
        $$;
        """
    )
    for table in TABLES:
        schema_editor.execute(
            f"""
            ALTER TABLE {table} OWNER TO custocrm_schema;
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            REVOKE ALL ON TABLE {table} FROM PUBLIC;
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO custocrm_runtime_app;
            GRANT ALL ON TABLE {table} TO custocrm_schema;
            CREATE POLICY custocrm_tenant_isolation ON {table}
                FOR ALL TO custocrm_runtime_app
                USING (organization_id = custocrm.current_organization_id())
                WITH CHECK (organization_id = custocrm.current_organization_id());
            CREATE POLICY custocrm_schema_access ON {table}
                FOR ALL TO custocrm_schema USING (true) WITH CHECK (true);
            """
        )
    for trigger, child, parent, column in RELATIONS:
        schema_editor.execute(
            f"""
            CREATE CONSTRAINT TRIGGER {trigger}
            AFTER INSERT OR UPDATE ON {child}
            DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
            custocrm.enforce_tenant_fk('{parent}', '{column}');
            """
        )
    schema_editor.execute(
        """
        CREATE OR REPLACE VIEW custocrm.support_portal_directory
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
        ALTER VIEW custocrm.support_portal_directory OWNER TO custocrm_schema;
        REVOKE ALL ON custocrm.support_portal_directory FROM PUBLIC;
        GRANT SELECT ON custocrm.support_portal_directory TO custocrm_runtime_platform;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public
            TO custocrm_runtime_app, custocrm_runtime_platform, custocrm_schema;
        """
    )


def uninstall(apps, schema_editor):
    schema_editor.execute("DROP VIEW IF EXISTS custocrm.support_portal_directory")
    for trigger, child, _parent, _column in RELATIONS:
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {child}")
    for table in TABLES:
        schema_editor.execute(
            f"""
            DROP POLICY IF EXISTS custocrm_tenant_isolation ON {table};
            DROP POLICY IF EXISTS custocrm_schema_access ON {table};
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
