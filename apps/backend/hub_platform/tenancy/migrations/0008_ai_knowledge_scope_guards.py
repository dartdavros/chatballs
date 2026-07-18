from django.db import migrations


TENANT_TABLES = ("ai_knowledgecategory", "ai_knowledgedepartment")
PLATFORM_POLICY = "custocrm_platform_tenant_provisioning"
TENANT_RELATIONS = (
    (
        "b01_knowledge_category_parent",
        "ai_knowledgecategory",
        "ai_knowledgecategory",
        "parent_id",
    ),
    ("b01_knowledge_category", "ai_knowledge", "ai_knowledgecategory", "category_id"),
    (
        "b02_knowledge_department_knowledge",
        "ai_knowledgedepartment",
        "ai_knowledge",
        "knowledge_id",
    ),
    (
        "b02_knowledge_department_department",
        "ai_knowledgedepartment",
        "identity_department",
        "department_id",
    ),
)


def add_scope_guards(apps, schema_editor):
    for table in TENANT_TABLES:
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
    schema_editor.execute(
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public "
        "TO custocrm_runtime_app, custocrm_runtime_platform, custocrm_schema"
    )
    schema_editor.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE ai_knowledgecategory "
        "TO custocrm_runtime_platform"
    )
    schema_editor.execute(
        f"""
        CREATE POLICY {PLATFORM_POLICY} ON ai_knowledgecategory
            FOR ALL TO custocrm_runtime_platform
            USING (organization_id = custocrm.current_organization_id())
            WITH CHECK (organization_id = custocrm.current_organization_id())
        """
    )
    for trigger, child, parent, column in TENANT_RELATIONS:
        schema_editor.execute(
            f"""
            CREATE CONSTRAINT TRIGGER {trigger}
            AFTER INSERT OR UPDATE ON {child}
            DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
            custocrm.enforce_tenant_fk('{parent}', '{column}');
            """
        )


def remove_scope_guards(apps, schema_editor):
    schema_editor.execute(
        f"DROP POLICY IF EXISTS {PLATFORM_POLICY} ON ai_knowledgecategory"
    )
    schema_editor.execute(
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE ai_knowledgecategory "
        "FROM custocrm_runtime_platform"
    )
    for trigger, child, _parent, _column in TENANT_RELATIONS:
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {child}")
    for table in TENANT_TABLES:
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
        ("tenancy", "0007_platform_row_select_policies"),
        ("ai", "0009_knowledge_hierarchy_and_visibility"),
    ]
    operations = [migrations.RunPython(add_scope_guards, remove_scope_guards)]
