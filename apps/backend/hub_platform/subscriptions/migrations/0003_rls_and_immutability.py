from django.db import migrations


GLOBAL_TABLES = (
    "subscriptions_plan",
    "subscriptions_planversion",
    "subscriptions_entitlementdefinition",
    "subscriptions_entitlementgrant",
    "subscriptions_quotadefinition",
    "subscriptions_quotagrant",
)

TENANT_TABLES = (
    "subscriptions_subscription",
    "subscriptions_subscriptionoverride",
    "subscriptions_usageperiod",
    "subscriptions_usageledgerentry",
    "subscriptions_usagecounter",
)

TENANT_FOREIGN_KEYS = (
    ("subscriptions_usageperiod", "subscriptions_subscription", "subscription_id"),
    ("subscriptions_usageledgerentry", "subscriptions_usageperiod", "period_id"),
    (
        "subscriptions_usageledgerentry",
        "subscriptions_usageledgerentry",
        "correction_of_id",
    ),
    ("subscriptions_usagecounter", "subscriptions_usageperiod", "period_id"),
)


def apply_boundaries(apps, schema_editor):
    schema_editor.execute(
        """
        CREATE OR REPLACE FUNCTION custocrm.prevent_published_plan_version_change()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.published_at IS NOT NULL THEN
                RAISE EXCEPTION 'published PlanVersion is immutable';
            END IF;
            IF TG_OP = 'UPDATE' AND NEW.published_at IS NOT NULL AND (
                NEW.plan_id IS DISTINCT FROM OLD.plan_id OR
                NEW.version IS DISTINCT FROM OLD.version OR
                NEW.agent_unit_price_minor IS DISTINCT FROM OLD.agent_unit_price_minor OR
                NEW.currency IS DISTINCT FROM OLD.currency OR
                NEW.billing_period IS DISTINCT FROM OLD.billing_period OR
                NEW.fixed_ai_agent_quantity IS DISTINCT FROM OLD.fixed_ai_agent_quantity OR
                NEW.effective_from IS DISTINCT FROM OLD.effective_from OR
                NEW.transition_rules IS DISTINCT FROM OLD.transition_rules
            ) THEN
                RAISE EXCEPTION 'PlanVersion cannot change while publishing';
            END IF;
            RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END $$;

        CREATE OR REPLACE FUNCTION custocrm.prevent_published_grant_change()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE version_id bigint;
        BEGIN
            version_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.plan_version_id
                               ELSE NEW.plan_version_id END;
            IF EXISTS (
                SELECT 1 FROM subscriptions_planversion
                WHERE id = version_id AND published_at IS NOT NULL
            ) THEN
                RAISE EXCEPTION 'grants of published PlanVersion are immutable';
            END IF;
            IF TG_OP = 'UPDATE' AND OLD.plan_version_id IS DISTINCT FROM NEW.plan_version_id
               AND EXISTS (
                   SELECT 1 FROM subscriptions_planversion
                   WHERE id = OLD.plan_version_id AND published_at IS NOT NULL
               ) THEN
                RAISE EXCEPTION 'grants of published PlanVersion are immutable';
            END IF;
            RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END $$;

        CREATE OR REPLACE FUNCTION custocrm.prevent_usage_ledger_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'usage ledger is append-only';
        END $$;

        ALTER FUNCTION custocrm.prevent_published_plan_version_change()
            OWNER TO custocrm_schema;
        ALTER FUNCTION custocrm.prevent_published_grant_change()
            OWNER TO custocrm_schema;
        ALTER FUNCTION custocrm.prevent_usage_ledger_mutation()
            OWNER TO custocrm_schema;
        REVOKE ALL ON FUNCTION custocrm.prevent_published_plan_version_change()
            FROM PUBLIC;
        REVOKE ALL ON FUNCTION custocrm.prevent_published_grant_change()
            FROM PUBLIC;
        REVOKE ALL ON FUNCTION custocrm.prevent_usage_ledger_mutation()
            FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION custocrm.prevent_published_plan_version_change(),
            custocrm.prevent_published_grant_change(),
            custocrm.prevent_usage_ledger_mutation(), custocrm.enforce_tenant_fk()
            TO custocrm_runtime_app, custocrm_runtime_platform, custocrm_schema;

        DROP TRIGGER IF EXISTS c05_plan_version_immutable ON subscriptions_planversion;
        CREATE TRIGGER c05_plan_version_immutable
            BEFORE UPDATE OR DELETE ON subscriptions_planversion
            FOR EACH ROW EXECUTE FUNCTION
            custocrm.prevent_published_plan_version_change();
        DROP TRIGGER IF EXISTS c05_entitlement_grant_immutable
            ON subscriptions_entitlementgrant;
        CREATE TRIGGER c05_entitlement_grant_immutable
            BEFORE INSERT OR UPDATE OR DELETE ON subscriptions_entitlementgrant
            FOR EACH ROW EXECUTE FUNCTION custocrm.prevent_published_grant_change();
        DROP TRIGGER IF EXISTS c05_quota_grant_immutable ON subscriptions_quotagrant;
        CREATE TRIGGER c05_quota_grant_immutable
            BEFORE INSERT OR UPDATE OR DELETE ON subscriptions_quotagrant
            FOR EACH ROW EXECUTE FUNCTION custocrm.prevent_published_grant_change();
        DROP TRIGGER IF EXISTS c05_usage_ledger_append_only
            ON subscriptions_usageledgerentry;
        CREATE TRIGGER c05_usage_ledger_append_only
            BEFORE UPDATE OR DELETE ON subscriptions_usageledgerentry
            FOR EACH ROW EXECUTE FUNCTION custocrm.prevent_usage_ledger_mutation();
        """
    )
    for table in GLOBAL_TABLES:
        schema_editor.execute(
            f"""
            ALTER TABLE {table} OWNER TO custocrm_schema;
            REVOKE ALL ON TABLE {table} FROM PUBLIC;
            GRANT SELECT ON TABLE {table}
                TO custocrm_runtime_app, custocrm_runtime_platform;
            GRANT INSERT, UPDATE, DELETE ON TABLE {table}
                TO custocrm_runtime_platform;
            GRANT ALL ON TABLE {table} TO custocrm_schema;
            """
        )
    for table in TENANT_TABLES:
        schema_editor.execute(
            f"""
            ALTER TABLE {table} OWNER TO custocrm_schema;
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            REVOKE ALL ON TABLE {table} FROM PUBLIC;
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table}
                TO custocrm_runtime_app, custocrm_runtime_platform;
            GRANT ALL ON TABLE {table} TO custocrm_schema;
            DROP POLICY IF EXISTS custocrm_subscription_tenant ON {table};
            CREATE POLICY custocrm_subscription_tenant ON {table}
                FOR ALL TO custocrm_runtime_app, custocrm_runtime_platform
                USING (organization_id = custocrm.current_organization_id())
                WITH CHECK (organization_id = custocrm.current_organization_id());
            DROP POLICY IF EXISTS custocrm_subscription_schema ON {table};
            CREATE POLICY custocrm_subscription_schema ON {table}
                FOR ALL TO custocrm_schema USING (true) WITH CHECK (true);
            """
        )
    schema_editor.execute(
        """
        REVOKE UPDATE, DELETE ON subscriptions_usageledgerentry
            FROM custocrm_runtime_app, custocrm_runtime_platform;
        REVOKE INSERT, UPDATE, DELETE ON subscriptions_subscriptionoverride
            FROM custocrm_runtime_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public
            TO custocrm_runtime_app, custocrm_runtime_platform, custocrm_schema;
        """
    )
    for index, (table, parent, column) in enumerate(TENANT_FOREIGN_KEYS):
        schema_editor.execute(
            f"""
            DROP TRIGGER IF EXISTS c05_tenant_fk_{index} ON {table};
            CREATE CONSTRAINT TRIGGER c05_tenant_fk_{index}
                AFTER INSERT OR UPDATE ON {table}
                DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
                custocrm.enforce_tenant_fk('{parent}', '{column}');
            """
        )


def remove_boundaries(apps, schema_editor):
    for index, (table, _parent, _column) in enumerate(TENANT_FOREIGN_KEYS):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS c05_tenant_fk_{index} ON {table}")
    for table in TENANT_TABLES:
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    schema_editor.execute(
        """
        DROP TRIGGER IF EXISTS c05_plan_version_immutable ON subscriptions_planversion;
        DROP TRIGGER IF EXISTS c05_entitlement_grant_immutable
            ON subscriptions_entitlementgrant;
        DROP TRIGGER IF EXISTS c05_quota_grant_immutable ON subscriptions_quotagrant;
        DROP TRIGGER IF EXISTS c05_usage_ledger_append_only
            ON subscriptions_usageledgerentry;
        DROP FUNCTION IF EXISTS custocrm.prevent_published_plan_version_change();
        DROP FUNCTION IF EXISTS custocrm.prevent_published_grant_change();
        DROP FUNCTION IF EXISTS custocrm.prevent_usage_ledger_mutation();
        """
    )


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0002_seed_plan_drafts"),
        ("tenancy", "0004_ingress_directory"),
    ]
    operations = [migrations.RunPython(apply_boundaries, remove_boundaries)]
