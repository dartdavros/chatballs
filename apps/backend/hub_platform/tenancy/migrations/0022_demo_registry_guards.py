# Реестр демо-данных (identity_demodataset, identity_demorecord): tenant-таблицы
# с organization_id, RLS и гранты по образцу tenancy/0021. Платформенная роль
# получает те же права: мастер первого запуска ставит демо-набор в очередь на
# соединении platform (SPEC-HUB-0021 §10).
from django.db import migrations

TABLES = ("identity_demodataset", "identity_demorecord")

FORWARD_RLS = """
ALTER TABLE {table} OWNER TO custocrm_schema;
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
REVOKE ALL ON {table} FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON {table}
    TO custocrm_runtime_app, custocrm_runtime_platform;
GRANT ALL ON {table} TO custocrm_schema;
GRANT USAGE, SELECT ON SEQUENCE {table}_id_seq
    TO custocrm_runtime_app, custocrm_runtime_platform, custocrm_schema;
DROP POLICY IF EXISTS custocrm_tenant_isolation ON {table};
CREATE POLICY custocrm_tenant_isolation ON {table}
    FOR ALL TO custocrm_runtime_app, custocrm_runtime_platform
    USING (organization_id = custocrm.current_organization_id())
    WITH CHECK (organization_id = custocrm.current_organization_id());
DROP POLICY IF EXISTS custocrm_schema_access ON {table};
CREATE POLICY custocrm_schema_access ON {table}
    FOR ALL TO custocrm_schema USING (true) WITH CHECK (true);
"""


def apply_guards(apps, schema_editor):
    for table in TABLES:
        schema_editor.execute(FORWARD_RLS.format(table=table))


def remove_guards(apps, schema_editor):
    for table in TABLES:
        schema_editor.execute(f"DROP POLICY IF EXISTS custocrm_tenant_isolation ON {table}")
        schema_editor.execute(f"DROP POLICY IF EXISTS custocrm_schema_access ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0021_chat_extras_guards"),
        ("identity", "0022_demo_dataset_registry"),
    ]

    operations = [migrations.RunPython(apply_guards, remove_guards)]
