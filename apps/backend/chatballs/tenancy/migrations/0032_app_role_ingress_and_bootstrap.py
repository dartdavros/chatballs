# Процесс backend-app держал platform-соединение ради двух вещей: чтения
# каталогов входа (виджет, портал, приглашение в звонок) и мастера первого
# запуска. Из-за этого пароль роли platform лежал в каждом процессе стека.
#
# Каталоги — security-barrier вьюхи над тенантными таблицами: они и задуманы как
# безопасный вход без tenant-контекста, роль app получает на них SELECT.
#
# Мастер первого запуска создаёт первую организацию. Право INSERT на
# identity_organization у роли app появляется под политикой «пока организаций
# нет»: проверку делает SECURITY DEFINER-функция от chatballs_schema (иначе
# политика ссылалась бы на свою же таблицу и Postgres отказал бы за рекурсию).
# После первой организации INSERT для app закрыт навсегда — создавать следующие
# по-прежнему может только роль platform (SPEC-HUB-0021 §10).
from django.db import migrations

INGRESS_VIEWS = (
    "attachment_directory",
    "call_invite_directory",
    "call_session_directory",
    "membership_directory",
    "organization_directory",
    "portal_article_file_directory",
    "support_portal_directory",
    "web_channel_directory",
    "web_session_directory",
    "web_widget_directory",
)

BOOTSTRAP_POLICY = "chatballs_organization_app_bootstrap"

BOOTSTRAP_SQL = f"""
CREATE OR REPLACE FUNCTION chatballs.instance_has_organizations() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
    SELECT EXISTS (SELECT 1 FROM identity_organization)
$$;
ALTER FUNCTION chatballs.instance_has_organizations() OWNER TO chatballs_schema;
REVOKE ALL ON FUNCTION chatballs.instance_has_organizations() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION chatballs.instance_has_organizations()
    TO chatballs_runtime_app, chatballs_schema;

GRANT INSERT ON identity_organization TO chatballs_runtime_app;
DROP POLICY IF EXISTS {BOOTSTRAP_POLICY} ON identity_organization;
CREATE POLICY {BOOTSTRAP_POLICY} ON identity_organization
    FOR INSERT TO chatballs_runtime_app
    WITH CHECK (NOT chatballs.instance_has_organizations());
"""

BOOTSTRAP_REVERSE_SQL = f"""
DROP POLICY IF EXISTS {BOOTSTRAP_POLICY} ON identity_organization;
REVOKE INSERT ON identity_organization FROM chatballs_runtime_app;
DROP FUNCTION IF EXISTS chatballs.instance_has_organizations();
"""


def grant_ingress(apps, schema_editor):
    for view in INGRESS_VIEWS:
        schema_editor.execute(f"GRANT SELECT ON chatballs.{view} TO chatballs_runtime_app")
    schema_editor.execute(BOOTSTRAP_SQL)


def revoke_ingress(apps, schema_editor):
    schema_editor.execute(BOOTSTRAP_REVERSE_SQL)
    for view in INGRESS_VIEWS:
        schema_editor.execute(f"REVOKE SELECT ON chatballs.{view} FROM chatballs_runtime_app")


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0031_platform_provisioning_table_grants"),
    ]

    operations = [migrations.RunPython(grant_ingress, revoke_ingress)]
