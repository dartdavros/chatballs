# ADR-HUB-0043: RLS, гранты и cross-tenant триггеры для групп сотрудников,
# плюс триггеры на новые group-FK каналов и диалогов. Стейл-записи Django для
# удалённых моделей отделов/профилей доступа вычищаются здесь же.
from django.db import migrations

GROUP_TABLES = ("identity_employeegroup", "identity_employeegroupmember")

FORWARD_RLS = """
ALTER TABLE {table} OWNER TO chatballs_schema;
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
REVOKE ALL ON {table} FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO chatballs_runtime_app;
GRANT ALL ON {table} TO chatballs_schema;
GRANT USAGE, SELECT ON SEQUENCE {table}_id_seq
    TO chatballs_runtime_app, chatballs_schema;
DROP POLICY IF EXISTS chatballs_tenant_isolation ON {table};
CREATE POLICY chatballs_tenant_isolation ON {table}
    FOR ALL TO chatballs_runtime_app
    USING (organization_id = chatballs.current_organization_id())
    WITH CHECK (organization_id = chatballs.current_organization_id());
DROP POLICY IF EXISTS chatballs_schema_access ON {table};
CREATE POLICY chatballs_schema_access ON {table}
    FOR ALL TO chatballs_schema USING (true) WITH CHECK (true);
"""

# (child, parent, fk_column) — как в 0002_cross_tenant_constraints.
GROUP_FOREIGN_KEYS = (
    ("identity_employeegroupmember", "identity_employeegroup", "group_id"),
    ("identity_employeegroupmember", "identity_employeeprofile", "employee_id"),
    ("channels_channel", "identity_employeegroup", "group_id"),
    ("conversations_conversation", "identity_employeegroup", "group_id"),
)


def apply_guards(apps, schema_editor):
    for table in GROUP_TABLES:
        schema_editor.execute(FORWARD_RLS.format(table=table))
    for index, (child, parent, fk_column) in enumerate(GROUP_FOREIGN_KEYS):
        schema_editor.execute(
            f"DROP TRIGGER IF EXISTS c04_group_tfk_{index} ON {child}"
        )
        schema_editor.execute(
            f"CREATE CONSTRAINT TRIGGER c04_group_tfk_{index} AFTER INSERT OR UPDATE ON {child} "
            "DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION "
            f"chatballs.enforce_tenant_fk('{parent}', '{fk_column}')"
        )
    # Стейл-записи contenttypes/permissions удалённых моделей (иначе migrate
    # --noinput оставляет их навсегда).
    schema_editor.execute(
        "DELETE FROM auth_permission WHERE content_type_id IN ("
        "SELECT id FROM django_content_type WHERE "
        "(app_label = 'identity' AND model IN ('department', 'accessprofile', "
        "'accessprofilecapability', 'employeeaccessassignment')) OR "
        "(app_label = 'ai' AND model = 'knowledgedepartment') OR "
        "(app_label = 'products' AND model = 'productdepartment'))"
    )
    schema_editor.execute(
        "DELETE FROM django_content_type WHERE "
        "(app_label = 'identity' AND model IN ('department', 'accessprofile', "
        "'accessprofilecapability', 'employeeaccessassignment')) OR "
        "(app_label = 'ai' AND model = 'knowledgedepartment') OR "
        "(app_label = 'products' AND model = 'productdepartment')"
    )


def remove_guards(apps, schema_editor):
    for index, (child, *_rest) in enumerate(GROUP_FOREIGN_KEYS):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS c04_group_tfk_{index} ON {child}")
    for table in GROUP_TABLES:
        schema_editor.execute(f"DROP POLICY IF EXISTS chatballs_tenant_isolation ON {table}")
        schema_editor.execute(f"DROP POLICY IF EXISTS chatballs_schema_access ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0017_drop_commerce"),
        ("identity", "0020_employeegroup_employeegroupmember_and_more"),
        ("channels", "0007_channel_group"),
        ("conversations", "0010_conversation_group"),
    ]

    operations = [migrations.RunPython(apply_guards, remove_guards)]
