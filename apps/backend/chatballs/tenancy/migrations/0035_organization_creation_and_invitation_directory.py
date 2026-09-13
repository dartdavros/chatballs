# Две дыры мультиорганизационности, обе на роли app.
#
# 1. Организации создаёт человек из интерфейса (кнопка «Добавить организацию»
#    в переключателе, дизайн-базлайн v2, A1), а не только оператор платформы.
#    Политика bootstrap из 0032 пускала INSERT роли app лишь до первой
#    организации. Теперь строка вставляется в контексте своего же id: сервис
#    заранее берёт id из последовательности (tenancy.lookup.reserve_organization_id),
#    открывает tenant_atomic(id) и уже в нём пишет строку — ровно так, как
#    это делал мастер первого запуска. Без контекста INSERT по-прежнему закрыт.
#
# 2. Ссылка-приглашение /join открывается без tenant-контекста: токен из
#    письма — единственное, что есть. Таблица приглашений под RLS, и роль app
#    без контекста не находила приглашение вовсе. Security-barrier каталог
#    invitation_directory отдаёт по хэшу токена id организации и приглашения —
#    по образцу call_invite_directory (0004).
from django.db import migrations

BOOTSTRAP_POLICY = "chatballs_organization_app_bootstrap"
CREATE_POLICY = "chatballs_organization_app_create"

FORWARD_SQL = f"""
DROP POLICY IF EXISTS {BOOTSTRAP_POLICY} ON identity_organization;
DROP POLICY IF EXISTS {CREATE_POLICY} ON identity_organization;
CREATE POLICY {CREATE_POLICY} ON identity_organization
    FOR INSERT TO chatballs_runtime_app
    WITH CHECK (id = chatballs.current_organization_id());

CREATE OR REPLACE VIEW chatballs.invitation_directory
WITH (security_barrier = true) AS
    SELECT invitation.id AS resource_id,
           invitation.organization_id,
           invitation.token_hash AS lookup_key
    FROM identity_organizationinvitation invitation;
ALTER VIEW chatballs.invitation_directory OWNER TO chatballs_schema;
REVOKE ALL ON chatballs.invitation_directory FROM PUBLIC;
GRANT SELECT ON chatballs.invitation_directory
    TO chatballs_runtime_app, chatballs_runtime_platform;
"""

REVERSE_SQL = f"""
DROP VIEW IF EXISTS chatballs.invitation_directory;
DROP POLICY IF EXISTS {CREATE_POLICY} ON identity_organization;
DROP POLICY IF EXISTS {BOOTSTRAP_POLICY} ON identity_organization;
CREATE POLICY {BOOTSTRAP_POLICY} ON identity_organization
    FOR INSERT TO chatballs_runtime_app
    WITH CHECK (NOT chatballs.instance_has_organizations());
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0034_update_state_grants"),
    ]

    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]
