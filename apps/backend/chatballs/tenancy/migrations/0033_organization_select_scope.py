# Роль app читала таблицу организаций целиком (0012: SELECT USING (true)) —
# любой процесс приложения без tenant-контекста мог перечислить чужие
# организации с именами, слагами и часовыми поясами. Теперь строка видна
# только в контексте своей организации. Входы без контекста (адрес, публичный
# id, слаг, id из outbox) идут через security-barrier каталог
# chatballs.organization_directory (tenancy/lookup), а мастер первого запуска
# спрашивает о наличии организаций SECURITY DEFINER-функцию (0032).
from django.db import migrations

SCOPED = """
DROP POLICY IF EXISTS chatballs_organization_app_select ON identity_organization;
CREATE POLICY chatballs_organization_app_select ON identity_organization
    FOR SELECT TO chatballs_runtime_app
    USING (id = chatballs.current_organization_id());
"""

UNSCOPED = """
DROP POLICY IF EXISTS chatballs_organization_app_select ON identity_organization;
CREATE POLICY chatballs_organization_app_select ON identity_organization
    FOR SELECT TO chatballs_runtime_app
    USING (true);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0032_app_role_ingress_and_bootstrap"),
    ]

    operations = [migrations.RunSQL(SCOPED, UNSCOPED)]
