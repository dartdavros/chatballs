# Дизайн-базлайн v2: RLS, гранты и cross-tenant триггеры для меток диалогов и
# шаблонов ответов. M2M «диалог-метка» получает indirect-политику и парный
# триггер по образцу ai_aiagent_knowledge_items (tenancy/0002/0003).
from django.db import migrations

ORG_TABLES = ("conversations_conversationlabel", "conversations_replytemplate")
M2M_TABLE = "conversations_conversation_labels"

FORWARD_RLS = """
ALTER TABLE {table} OWNER TO custocrm_schema;
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
REVOKE ALL ON {table} FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO custocrm_runtime_app;
GRANT ALL ON {table} TO custocrm_schema;
GRANT USAGE, SELECT ON SEQUENCE {table}_id_seq
    TO custocrm_runtime_app, custocrm_schema;
DROP POLICY IF EXISTS custocrm_tenant_isolation ON {table};
CREATE POLICY custocrm_tenant_isolation ON {table}
    FOR ALL TO custocrm_runtime_app
    USING (organization_id = custocrm.current_organization_id())
    WITH CHECK (organization_id = custocrm.current_organization_id());
DROP POLICY IF EXISTS custocrm_schema_access ON {table};
CREATE POLICY custocrm_schema_access ON {table}
    FOR ALL TO custocrm_schema USING (true) WITH CHECK (true);
"""

M2M_RLS = f"""
ALTER TABLE {M2M_TABLE} OWNER TO custocrm_schema;
ALTER TABLE {M2M_TABLE} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {M2M_TABLE} FORCE ROW LEVEL SECURITY;
REVOKE ALL ON {M2M_TABLE} FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON {M2M_TABLE} TO custocrm_runtime_app;
GRANT ALL ON {M2M_TABLE} TO custocrm_schema;
GRANT USAGE, SELECT ON SEQUENCE {M2M_TABLE}_id_seq
    TO custocrm_runtime_app, custocrm_schema;
DROP POLICY IF EXISTS custocrm_tenant_isolation ON {M2M_TABLE};
CREATE POLICY custocrm_tenant_isolation ON {M2M_TABLE}
    FOR ALL TO custocrm_runtime_app
    USING (
        EXISTS (
            SELECT 1 FROM conversations_conversation conversation
            JOIN conversations_conversationlabel label ON label.id = conversationlabel_id
            WHERE conversation.id = conversation_id
              AND conversation.organization_id = custocrm.current_organization_id()
              AND label.organization_id = conversation.organization_id
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM conversations_conversation conversation
            JOIN conversations_conversationlabel label ON label.id = conversationlabel_id
            WHERE conversation.id = conversation_id
              AND conversation.organization_id = custocrm.current_organization_id()
              AND label.organization_id = conversation.organization_id
        )
    );
DROP POLICY IF EXISTS custocrm_schema_access ON {M2M_TABLE};
CREATE POLICY custocrm_schema_access ON {M2M_TABLE}
    FOR ALL TO custocrm_schema USING (true) WITH CHECK (true);
"""


def apply_guards(apps, schema_editor):
    for table in ORG_TABLES:
        schema_editor.execute(FORWARD_RLS.format(table=table))
    schema_editor.execute(M2M_RLS)
    schema_editor.execute(
        f"DROP TRIGGER IF EXISTS c04_label_tpair ON {M2M_TABLE}"
    )
    schema_editor.execute(
        f"CREATE CONSTRAINT TRIGGER c04_label_tpair AFTER INSERT OR UPDATE ON {M2M_TABLE} "
        "DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION "
        "custocrm.enforce_tenant_pair('conversations_conversation', 'conversation_id', "
        "'conversations_conversationlabel', 'conversationlabel_id')"
    )


def remove_guards(apps, schema_editor):
    schema_editor.execute(f"DROP TRIGGER IF EXISTS c04_label_tpair ON {M2M_TABLE}")
    for table in (*ORG_TABLES, M2M_TABLE):
        schema_editor.execute(f"DROP POLICY IF EXISTS custocrm_tenant_isolation ON {table}")
        schema_editor.execute(f"DROP POLICY IF EXISTS custocrm_schema_access ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0020_drop_billing"),
        ("conversations", "0011_conversation_archived_at_conversation_note_and_more"),
    ]

    operations = [migrations.RunPython(apply_guards, remove_guards)]
