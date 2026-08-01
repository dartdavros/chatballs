"""Гарды тенанта для связи агента со статьями портала поддержки.

Связь `ai_aiagent_portal_articles` — автоматическая M2M-таблица без
`organization_id`, поэтому изоляция строится тем же косвенным EXISTS-правилом,
что и `ai_aiagent_knowledge_items` (tenancy/0003). Дополнительно фрагменты
знаний получают источник `portal_article_id`, который тоже обязан принадлежать
организации строки.
"""

from django.db import migrations

LINK_TABLE = "ai_aiagent_portal_articles"
LINK_POLICY = """
    EXISTS (
        SELECT 1 FROM ai_aiagent agent
        JOIN support_portals_portalarticle article ON article.id = portalarticle_id
        WHERE agent.id = aiagent_id
          AND agent.organization_id = custocrm.current_organization_id()
          AND article.organization_id = agent.organization_id
    )
"""


def install(apps, schema_editor):
    schema_editor.execute(
        f"""
        ALTER TABLE {LINK_TABLE} OWNER TO custocrm_schema;
        ALTER TABLE {LINK_TABLE} ENABLE ROW LEVEL SECURITY;
        ALTER TABLE {LINK_TABLE} FORCE ROW LEVEL SECURITY;
        REVOKE ALL ON TABLE {LINK_TABLE} FROM PUBLIC;
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {LINK_TABLE} TO custocrm_runtime_app;
        GRANT ALL ON TABLE {LINK_TABLE} TO custocrm_schema;
        DROP POLICY IF EXISTS custocrm_tenant_isolation ON {LINK_TABLE};
        CREATE POLICY custocrm_tenant_isolation ON {LINK_TABLE}
            FOR ALL TO custocrm_runtime_app
            USING ({LINK_POLICY}) WITH CHECK ({LINK_POLICY});
        DROP POLICY IF EXISTS custocrm_schema_access ON {LINK_TABLE};
        CREATE POLICY custocrm_schema_access ON {LINK_TABLE}
            FOR ALL TO custocrm_schema USING (true) WITH CHECK (true);
        """
    )
    schema_editor.execute(
        f"""
        CREATE CONSTRAINT TRIGGER apa_agent_article_pair
        AFTER INSERT OR UPDATE ON {LINK_TABLE}
        DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
        custocrm.enforce_tenant_pair(
            'ai_aiagent', 'aiagent_id',
            'support_portals_portalarticle', 'portalarticle_id'
        );
        """
    )
    schema_editor.execute(
        """
        CREATE CONSTRAINT TRIGGER apa_fragment_article
        AFTER INSERT OR UPDATE ON ai_knowledgefragment
        DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
        custocrm.enforce_tenant_fk(
            'support_portals_portalarticle', 'portal_article_id'
        );
        """
    )


def remove(apps, schema_editor):
    schema_editor.execute(
        "DROP TRIGGER IF EXISTS apa_fragment_article ON ai_knowledgefragment"
    )
    schema_editor.execute(f"DROP TRIGGER IF EXISTS apa_agent_article_pair ON {LINK_TABLE}")
    schema_editor.execute(
        f"""
        DROP POLICY IF EXISTS custocrm_tenant_isolation ON {LINK_TABLE};
        DROP POLICY IF EXISTS custocrm_schema_access ON {LINK_TABLE};
        ALTER TABLE {LINK_TABLE} NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE {LINK_TABLE} DISABLE ROW LEVEL SECURITY;
        """
    )


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0013_storage_reservation_rls"),
        ("ai", "0013_portal_article_knowledge"),
    ]
    operations = [migrations.RunPython(install, remove)]
