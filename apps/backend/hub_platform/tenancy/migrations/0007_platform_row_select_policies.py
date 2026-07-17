from django.db import migrations

# Django ORM inserts use INSERT ... RETURNING id; PostgreSQL applies SELECT
# policies to rows returned by RETURNING, so the app role needs SELECT
# visibility of the platform-scope rows it is allowed to insert
# (custocrm_app_platform_audit_insert / custocrm_app_platform_outbox_insert).
# Without these policies a login-failed audit write fails with
# "new row violates row-level security policy".
CREATE_POLICIES = """
DROP POLICY IF EXISTS custocrm_app_platform_audit_select ON identity_auditevent;
CREATE POLICY custocrm_app_platform_audit_select ON identity_auditevent
    FOR SELECT TO custocrm_runtime_app USING (organization_id IS NULL);
DROP POLICY IF EXISTS custocrm_app_platform_outbox_select ON events_outboxevent;
CREATE POLICY custocrm_app_platform_outbox_select ON events_outboxevent
    FOR SELECT TO custocrm_runtime_app
    USING (ownership = 'PLATFORM' AND organization_id IS NULL);
"""

DROP_POLICIES = """
DROP POLICY IF EXISTS custocrm_app_platform_audit_select ON identity_auditevent;
DROP POLICY IF EXISTS custocrm_app_platform_outbox_select ON events_outboxevent;
"""


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0006_storage_reserved_bytes")]
    operations = [migrations.RunSQL(CREATE_POLICIES, DROP_POLICIES)]
