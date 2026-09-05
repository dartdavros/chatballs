# Удаление пользователя runtime-ролью (снятие демо-набора удаляет демо-сотрудников):
# каскад Django проходит по django_admin_log и M2M-таблицам пользователя, на
# которые у app/platform были только SELECT-права — удаление падало с
# «permission denied for table django_admin_log».
from django.db import migrations

FORWARD = """
GRANT SELECT, DELETE ON django_admin_log, identity_humanuser_groups, identity_humanuser_user_permissions
    TO custocrm_runtime_app, custocrm_runtime_platform;
"""

BACKWARD = """
REVOKE DELETE ON django_admin_log, identity_humanuser_groups, identity_humanuser_user_permissions
    FROM custocrm_runtime_app, custocrm_runtime_platform;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0022_demo_registry_guards"),
        ("admin", "0003_logentry_add_action_flag_choices"),
    ]

    operations = [migrations.RunSQL(FORWARD, BACKWARD)]
