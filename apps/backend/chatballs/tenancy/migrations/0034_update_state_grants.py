# Состояние обновлений установки (updates_updatestate): одна строка на
# инсталляцию, не тенантная таблица, без RLS — как настройки установки (0028).
# Пишут её приложение (запрос установки, синхронизация статуса) и воркер
# (периодическая проверка канала релизов) — оба ролью app.
from django.db import migrations

GRANTS = """
GRANT SELECT, INSERT, UPDATE ON updates_updatestate
    TO chatballs_runtime_app, chatballs_runtime_platform;
GRANT USAGE, SELECT ON SEQUENCE updates_updatestate_id_seq
    TO chatballs_runtime_app, chatballs_runtime_platform;
"""

REVOKE = """
REVOKE ALL ON updates_updatestate
    FROM chatballs_runtime_app, chatballs_runtime_platform;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0033_organization_select_scope"),
        ("updates", "0001_initial"),
    ]

    operations = [migrations.RunSQL(GRANTS, REVOKE)]
