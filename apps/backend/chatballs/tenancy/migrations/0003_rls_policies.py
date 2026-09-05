from django.db import migrations


TENANT_TABLES = (
    "identity_department",
    "identity_employeeprofile",
    "identity_accessprofile",
    "identity_accessprofilecapability",
    "identity_employeeaccessassignment",
    "identity_organizationinvitation",
    "identity_auditevent",
    "identity_product",
    "tenancy_organizationstorageusage",
    "products_productdepartment",
    "products_offer",
    "products_price",
    "products_marketplacepublication",
    "ai_knowledge",
    "ai_knowledgeattachment",
    "ai_knowledgefragment",
    "ai_aiagent",
    "ai_llminvocation",
    "integrations_integration",
    "channels_channel",
    "conversations_contact",
    "conversations_connectionidentity",
    "conversations_conversation",
    "conversations_conversationread",
    "conversations_message",
    # Таблицы orders_*/sales_* удалены вместе с приложениями (ADR-HUB-0041).
    "support_productsupportcontract",
    "support_supportidentitysnapshot",
    "calls_callsession",
    "calls_callinvite",
    "calls_callparticipant",
    "calls_callmetric",
    "notifications_notification",
    "notifications_notificationread",
    "notifications_messengerbinding",
    "notifications_messengerbindingcode",
    "webchat_websession",
    "events_outboxevent",
    "events_inboxevent",
)

INDIRECT_TABLE_POLICIES = {
    "ai_aiagent_knowledge_items": """
        EXISTS (
            SELECT 1 FROM ai_aiagent agent
            JOIN ai_knowledge knowledge ON knowledge.id = knowledge_id
            WHERE agent.id = aiagent_id
              AND agent.organization_id = chatballs.current_organization_id()
              AND knowledge.organization_id = agent.organization_id
        )
    """,
    "support_productsupportcontract_allowed_channels": """
        EXISTS (
            SELECT 1 FROM support_productsupportcontract contract
            JOIN channels_channel channel ON channel.id = channel_id
            WHERE contract.id = productsupportcontract_id
              AND contract.organization_id = chatballs.current_organization_id()
              AND channel.organization_id = contract.organization_id
        )
    """,
}

MIXED_PLATFORM_TABLES = (
    "identity_auditevent",
    "events_outboxevent",
    "events_inboxevent",
)


def _ensure_roles(schema_editor):
    schema_editor.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'chatballs_runtime_app') THEN
                CREATE ROLE chatballs_runtime_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'chatballs_runtime_platform') THEN
                CREATE ROLE chatballs_runtime_platform NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'chatballs_schema') THEN
                CREATE ROLE chatballs_schema NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
            END IF;
            IF NOT pg_has_role(current_user, 'chatballs_schema', 'MEMBER') THEN
                EXECUTE format('GRANT chatballs_schema TO %%I', current_user);
            END IF;
        END $$;

        CREATE SCHEMA IF NOT EXISTS chatballs AUTHORIZATION chatballs_schema;
        ALTER SCHEMA chatballs OWNER TO chatballs_schema;
        REVOKE ALL ON SCHEMA chatballs FROM PUBLIC;
        GRANT USAGE ON SCHEMA chatballs TO chatballs_runtime_app, chatballs_runtime_platform;

        CREATE OR REPLACE FUNCTION chatballs.current_organization_id() RETURNS bigint
        LANGUAGE sql STABLE PARALLEL SAFE AS $$
            SELECT CASE
                WHEN current_setting('chatballs.organization_id', true) ~ '^[1-9][0-9]*$'
                THEN current_setting('chatballs.organization_id', true)::bigint
                ELSE NULL
            END
        $$;
        ALTER FUNCTION chatballs.current_organization_id() OWNER TO chatballs_schema;
        ALTER FUNCTION chatballs.enforce_tenant_fk() OWNER TO chatballs_schema;
        ALTER FUNCTION chatballs.enforce_tenant_user() OWNER TO chatballs_schema;
        ALTER FUNCTION chatballs.enforce_tenant_pair() OWNER TO chatballs_schema;
        REVOKE ALL ON FUNCTION chatballs.current_organization_id() FROM PUBLIC;
        REVOKE ALL ON FUNCTION chatballs.enforce_tenant_fk() FROM PUBLIC;
        REVOKE ALL ON FUNCTION chatballs.enforce_tenant_user() FROM PUBLIC;
        REVOKE ALL ON FUNCTION chatballs.enforce_tenant_pair() FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION chatballs.current_organization_id()
            TO chatballs_runtime_app, chatballs_runtime_platform;
        GRANT EXECUTE ON FUNCTION chatballs.enforce_tenant_fk(),
            chatballs.enforce_tenant_user(), chatballs.enforce_tenant_pair()
            TO chatballs_runtime_app, chatballs_schema;
        GRANT USAGE ON SCHEMA public TO chatballs_runtime_app, chatballs_runtime_platform;
        """
    )


def enable_rls(apps, schema_editor):
    _ensure_roles(schema_editor)
    for table in TENANT_TABLES:
        schema_editor.execute(
            f"""
            ALTER TABLE {table} OWNER TO chatballs_schema;
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            REVOKE ALL ON TABLE {table} FROM PUBLIC;
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO chatballs_runtime_app;
            GRANT ALL ON TABLE {table} TO chatballs_schema;
            DROP POLICY IF EXISTS chatballs_tenant_isolation ON {table};
            CREATE POLICY chatballs_tenant_isolation ON {table}
                FOR ALL TO chatballs_runtime_app
                USING (organization_id = chatballs.current_organization_id())
                WITH CHECK (organization_id = chatballs.current_organization_id());
            DROP POLICY IF EXISTS chatballs_schema_access ON {table};
            CREATE POLICY chatballs_schema_access ON {table}
                FOR ALL TO chatballs_schema USING (true) WITH CHECK (true);
            """
        )
    for table, expression in INDIRECT_TABLE_POLICIES.items():
        schema_editor.execute(
            f"""
            ALTER TABLE {table} OWNER TO chatballs_schema;
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            REVOKE ALL ON TABLE {table} FROM PUBLIC;
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO chatballs_runtime_app;
            GRANT ALL ON TABLE {table} TO chatballs_schema;
            DROP POLICY IF EXISTS chatballs_tenant_isolation ON {table};
            CREATE POLICY chatballs_tenant_isolation ON {table}
                FOR ALL TO chatballs_runtime_app
                USING ({expression}) WITH CHECK ({expression});
            DROP POLICY IF EXISTS chatballs_schema_access ON {table};
            CREATE POLICY chatballs_schema_access ON {table}
                FOR ALL TO chatballs_schema USING (true) WITH CHECK (true);
            """
        )
    for table in MIXED_PLATFORM_TABLES:
        schema_editor.execute(
            f"""
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO chatballs_runtime_platform;
            DROP POLICY IF EXISTS chatballs_platform_boundary ON {table};
            CREATE POLICY chatballs_platform_boundary ON {table}
                FOR ALL TO chatballs_runtime_platform USING (true) WITH CHECK (true);
            """
        )
    schema_editor.execute(
        """
        DROP POLICY IF EXISTS chatballs_app_platform_audit_insert ON identity_auditevent;
        CREATE POLICY chatballs_app_platform_audit_insert ON identity_auditevent
            FOR INSERT TO chatballs_runtime_app WITH CHECK (organization_id IS NULL);
        DROP POLICY IF EXISTS chatballs_app_platform_outbox_insert ON events_outboxevent;
        CREATE POLICY chatballs_app_platform_outbox_insert ON events_outboxevent
            FOR INSERT TO chatballs_runtime_app
            WITH CHECK (ownership = 'PLATFORM' AND organization_id IS NULL);

        GRANT SELECT ON identity_organization TO chatballs_runtime_app, chatballs_runtime_platform;
        GRANT SELECT, INSERT, UPDATE, DELETE ON identity_humanuser
            TO chatballs_runtime_app, chatballs_runtime_platform;
        GRANT SELECT, INSERT, UPDATE, DELETE ON django_session
            TO chatballs_runtime_app, chatballs_runtime_platform;
        GRANT SELECT ON django_content_type, auth_permission, auth_group,
            auth_group_permissions, identity_humanuser_groups, identity_humanuser_user_permissions
            TO chatballs_runtime_app, chatballs_runtime_platform;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public
            TO chatballs_runtime_app, chatballs_runtime_platform, chatballs_schema;
        """
    )


def disable_rls(apps, schema_editor):
    for table in (*TENANT_TABLES, *INDIRECT_TABLE_POLICIES):
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    # sessions/auth/contenttypes — явно: миграция выдаёт GRANT на django_session,
    # auth_permission и django_content_type; раньше порядок обеспечивался
    # транзитивно через удалённые приложения orders/sales (ADR-HUB-0041).
    dependencies = [
        ("tenancy", "0002_cross_tenant_constraints"),
        ("sessions", "0001_initial"),
        ("auth", "0001_initial"),
        ("contenttypes", "0001_initial"),
    ]
    operations = [migrations.RunPython(enable_rls, disable_rls)]
