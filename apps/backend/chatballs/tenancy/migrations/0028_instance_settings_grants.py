# Настройки установки (identity_instancesettings): одна строка на инсталляцию,
# не тенантная таблица, без RLS — как tenancy/0025 для настроек хранилища.
# Мастер первого запуска пишет её на платформенном соединении, приложение читает.
from django.db import migrations

GRANTS = """
GRANT SELECT, INSERT, UPDATE ON identity_instancesettings
    TO chatballs_runtime_app, chatballs_runtime_platform;
GRANT USAGE, SELECT ON SEQUENCE identity_instancesettings_id_seq
    TO chatballs_runtime_app, chatballs_runtime_platform;
"""

REVOKE = """
REVOKE ALL ON identity_instancesettings
    FROM chatballs_runtime_app, chatballs_runtime_platform;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0027_portal_article_file_guards"),
        ("identity", "0027_instance_settings"),
    ]

    operations = [migrations.RunSQL(GRANTS, REVOKE)]
