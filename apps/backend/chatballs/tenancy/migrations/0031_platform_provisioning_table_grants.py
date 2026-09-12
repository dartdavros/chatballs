# Таблицы платформенного приложения (operator, token, provisioning) появились
# после tenancy/0003, и ни одна миграция не выдала на них прав runtime-роли
# platform. В деплое backend-platform работает ролью chatballs_platform, поэтому
# уже проверка токена падала «permission denied for table platform_platformtoken»,
# а вместе с ней — весь POST /api/v1/organizations (SPEC-HUB-0021 §12). Тесты
# этого не видели: они ходят в базу владельцем кластера.
#
# Здесь роль platform получает DML на платформенные таблицы (без DELETE: токены
# отзываются, записи провижининга хранятся) и на приглашения — их выписывает тот
# же провижининг для будущего владельца внутри set_local_tenant(new_org_id), под
# той же tenant-политикой, что в 0005 для членств.
from django.db import migrations

PLATFORM_POLICY = "chatballs_platform_tenant_provisioning"

GRANTS = f"""
GRANT SELECT, INSERT, UPDATE ON platform_platformoperator, platform_platformtoken,
    platform_organizationprovisioning TO chatballs_runtime_platform;
GRANT USAGE, SELECT ON SEQUENCE platform_platformoperator_id_seq,
    platform_platformtoken_id_seq, platform_organizationprovisioning_id_seq
    TO chatballs_runtime_platform;

GRANT SELECT, INSERT, UPDATE ON identity_organizationinvitation
    TO chatballs_runtime_platform;
GRANT USAGE, SELECT ON SEQUENCE identity_organizationinvitation_id_seq
    TO chatballs_runtime_platform;
DROP POLICY IF EXISTS {PLATFORM_POLICY} ON identity_organizationinvitation;
CREATE POLICY {PLATFORM_POLICY} ON identity_organizationinvitation
    FOR ALL TO chatballs_runtime_platform
    USING (organization_id = chatballs.current_organization_id())
    WITH CHECK (organization_id = chatballs.current_organization_id());
"""

REVOKE = f"""
DROP POLICY IF EXISTS {PLATFORM_POLICY} ON identity_organizationinvitation;
REVOKE ALL ON identity_organizationinvitation FROM chatballs_runtime_platform;
REVOKE ALL ON SEQUENCE identity_organizationinvitation_id_seq
    FROM chatballs_runtime_platform;
REVOKE ALL ON platform_platformoperator, platform_platformtoken,
    platform_organizationprovisioning FROM chatballs_runtime_platform;
REVOKE ALL ON SEQUENCE platform_platformoperator_id_seq,
    platform_platformtoken_id_seq, platform_organizationprovisioning_id_seq
    FROM chatballs_runtime_platform;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0030_encrypted_column_widths"),
        ("platform", "0001_initial"),
    ]

    operations = [migrations.RunSQL(GRANTS, REVOKE)]
