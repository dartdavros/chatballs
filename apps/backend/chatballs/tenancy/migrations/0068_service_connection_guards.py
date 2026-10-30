# Сервисные подключения (SPEC-0037 R-2, R-7): настройки адаптера, OAuth state и
# операционные файлы — tenant-таблицы с RLS и проверкой, что связанное
# подключение принадлежит той же организации. Образец — tenancy/0040.
from django.db import migrations

# таблица → (родительская таблица, колонка связи)
TABLES = {
    "integrations_serviceconnectionsettings": (
        ("integrations_integration", "integration_id"),
    ),
    "integrations_serviceoauthstate": (
        ("integrations_integration", "integration_id"),
        ("integrations_integration", "result_id"),
    ),
    "integrations_servicefile": (
        ("integrations_integration", "integration_id"),
    ),
}

FORWARD_RLS = """
ALTER TABLE {table} OWNER TO chatballs_schema;
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE {table} FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO chatballs_runtime_app;
GRANT ALL ON TABLE {table} TO chatballs_schema;
GRANT USAGE, SELECT ON SEQUENCE {table}_id_seq TO chatballs_runtime_app, chatballs_schema;
DROP POLICY IF EXISTS chatballs_tenant_isolation ON {table};
CREATE POLICY chatballs_tenant_isolation ON {table}
    FOR ALL TO chatballs_runtime_app
    USING (organization_id = chatballs.current_organization_id())
    WITH CHECK (organization_id = chatballs.current_organization_id());
DROP POLICY IF EXISTS chatballs_schema_access ON {table};
CREATE POLICY chatballs_schema_access ON {table}
    FOR ALL TO chatballs_schema USING (true) WITH CHECK (true);
"""

FORWARD_TRIGGER = """
CREATE CONSTRAINT TRIGGER {table}_{column}_tenant
AFTER INSERT OR UPDATE ON {table}
DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
chatballs.enforce_tenant_fk('{parent}', '{column}');
"""


def apply_guards(apps, schema_editor):
    for table, relations in TABLES.items():
        schema_editor.execute(FORWARD_RLS.format(table=table))
        for parent, column in relations:
            schema_editor.execute(
                FORWARD_TRIGGER.format(table=table, parent=parent, column=column)
            )


def remove_guards(apps, schema_editor):
    for table, relations in TABLES.items():
        for _parent, column in relations:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {table}_{column}_tenant ON {table}")
        schema_editor.execute(f"DROP POLICY IF EXISTS chatballs_tenant_isolation ON {table}")
        schema_editor.execute(f"DROP POLICY IF EXISTS chatballs_schema_access ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        schema_editor.execute(f"REVOKE ALL ON TABLE {table} FROM chatballs_runtime_app")
        schema_editor.execute(
            f"REVOKE USAGE, SELECT ON SEQUENCE {table}_id_seq FROM chatballs_runtime_app"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0067_skill_library_guards"),
        ("integrations", "0015_service_connections"),
    ]

    operations = [migrations.RunPython(apply_guards, remove_guards)]
