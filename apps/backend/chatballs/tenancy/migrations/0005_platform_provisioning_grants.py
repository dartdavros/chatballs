# C06 tenant provisioning DB boundary (SPEC-HUB-0021 §10, ADR-CHATBALLS-0029 §6).
#
# Provisioning runs on the platform connection (chatballs_runtime_platform) and must
# both INSERT a new Organization and create tenant-owned rows (departments, the
# OWNER membership) inside set_local_tenant(new_org_id). Today identity_organization
# has only GRANT SELECT to runtime roles, and identity_department /
# identity_employeeprofile grant DML to chatballs_runtime_app only. This migration
# extends the platform role with the minimal grants and tenant-isolation policies
# it needs, mirroring the subscriptions tenant policy (both roles, matching tenant
# context only). It does not weaken isolation: the platform role still cannot read
# or write tenant rows without the matching transaction-local tenant context.
from django.db import migrations

# identity_department and identity_employeeprofile are already ENABLE/FORCE RLS in
# 0003 for chatballs_runtime_app. Here we grant the platform role DML and add a
# tenant-isolation policy identical in shape to the subscriptions policy, so the
# platform role sees only matching tenant context. organization_id is the direct
# tenant key on both tables (0002_cross_tenant_constraints / 0012 membership).
PROVISIONING_TENANT_TABLES = (
    "identity_department",
    "identity_employeeprofile",
)

PLATFORM_POLICY = "chatballs_platform_tenant_provisioning"


def apply_grants(apps, schema_editor):
    # 1. Platform role may create and update organizations (no RLS on this table;
    #    it has no organization_id column). DELETE stays with the schema/migration
    #    role per SPEC-HUB-0021 §14 (hard delete as compensation is forbidden).
    schema_editor.execute(
        "GRANT INSERT, UPDATE ON identity_organization TO chatballs_runtime_platform"
    )

    # 2. For each provisioning tenant table: grant DML to the platform role and add
    #    a tenant-isolation policy mirroring chatballs_subscription_tenant.
    for table in PROVISIONING_TENANT_TABLES:
        schema_editor.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO chatballs_runtime_platform"
        )
        schema_editor.execute(f"DROP POLICY IF EXISTS {PLATFORM_POLICY} ON {table}")
        schema_editor.execute(
            f"""
            CREATE POLICY {PLATFORM_POLICY} ON {table}
                FOR ALL TO chatballs_runtime_platform
                USING (organization_id = chatballs.current_organization_id())
                WITH CHECK (organization_id = chatballs.current_organization_id())
            """
        )

    # 3. organization_directory: minimal platform-readable lookup public_id -> id.
    #    identity_organization is already GRANT SELECT to the platform role, so a
    #    plain security-barrier view is sufficient and consistent with 0004.
    schema_editor.execute(
        """
        CREATE OR REPLACE VIEW chatballs.organization_directory
        WITH (security_barrier = true) AS
            SELECT id AS organization_id, public_id, status, slug
            FROM identity_organization
        """
    )
    schema_editor.execute("ALTER VIEW chatballs.organization_directory OWNER TO chatballs_schema")
    schema_editor.execute("REVOKE ALL ON chatballs.organization_directory FROM PUBLIC")
    schema_editor.execute(
        "GRANT SELECT ON chatballs.organization_directory TO chatballs_runtime_platform"
    )


def revert_grants(apps, schema_editor):
    schema_editor.execute("DROP VIEW IF EXISTS chatballs.organization_directory")
    for table in PROVISIONING_TENANT_TABLES:
        schema_editor.execute(f"DROP POLICY IF EXISTS {PLATFORM_POLICY} ON {table}")
        schema_editor.execute(
            f"REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE {table} FROM chatballs_runtime_platform"
        )
    schema_editor.execute(
        "REVOKE INSERT, UPDATE ON identity_organization FROM chatballs_runtime_platform"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0004_ingress_directory"),
        ("identity", "0015_organization_status"),
    ]
    operations = [migrations.RunPython(apply_grants, revert_grants)]
